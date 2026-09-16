from datetime import timedelta
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.account_export import export_account
from api.domain.user.account_service import delete_account
from api.domain.user.dependencies import get_current_user, require_admin
from api.domain.user.exceptions import (
    EmailAlreadyTakenError,
    InstanceFullError,
    InvalidCurrentPasswordError,
    InvalidInvitationError,
    InvalidMagicLinkTokenError,
    InvalidRefreshTokenError,
    InvalidSsoLoginAttemptError,
    InvalidTotpCodeError,
    LastAdminError,
    SsoNotConfiguredError,
    SsoSubjectMismatchError,
    TotpAlreadyEnabledError,
    TotpNotEnrolledError,
    TotpRequiredError,
)
from api.domain.user.invitation_service import (
    accept_invitation,
    invite_member,
    list_pending_invitations,
    revoke_invitation,
)
from api.domain.user.magic_link_service import request_magic_link, verify_magic_link_token
from api.domain.user.models import Instance, Invitation, Role, User
from api.domain.user.oidc_login_service import consume_login_attempt, start_login_attempt
from api.domain.user.password_service import change_password, reset_password
from api.domain.user.refresh_token_service import (
    issue_refresh_token,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from api.domain.user.schemas import (
    AccountExportResponse,
    DeleteAccountRequest,
    InvitationAcceptRequest,
    InvitationRequest,
    InvitationResponse,
    LoginRequest,
    LogoutRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    MeResponse,
    MeUpdateRequest,
    OnboardingAdminRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    RefreshRequest,
    SecondFactorFields,
    SsoCallbackRequest,
    TokenPairResponse,
    TotpConfirmRequest,
    TotpDisableRequest,
    TotpEnrolmentResponse,
    TotpRecoveryCodesResponse,
)
from api.domain.user.sso_service import (
    SsoConfiguration,
    get_or_create_sso_user,
    read_sso_configuration,
)
from api.domain.user.totp_service import (
    SecondFactor,
    begin_enrolment,
    confirm_enrolment,
    count_unused_recovery_codes,
    disable_totp,
    is_totp_enabled,
    regenerate_recovery_codes,
    verify_second_factor,
)
from api.technical.auth.hashing import hash_password, verify_password
from api.technical.auth.jwt import create_access_token
from api.technical.auth.oidc_client import (
    InsecureIssuerError,
    InvalidIdTokenError,
    OidcDiscoveryDocument,
    build_authorize_url,
    discover,
    exchange_code_for_tokens,
    fetch_jwks,
    fetch_userinfo,
    get_oidc_transport,
    verify_id_token,
)
from api.technical.crypto.secret_box import decrypt_secret, encrypt_secret
from api.technical.db import get_db_session
from api.technical.rate_limit.dependencies import client_address, enforce
from api.technical.rate_limit.limiter import RateLimiter, get_rate_limiter
from config.instance import get_instance_config
from config.rate_limit import get_rate_limit_config

router = APIRouter()


async def _enforce_token_guessing_limit(
    limiter: RateLimiter, request: Request, *, scope: str
) -> None:
    """Caps the routes that take an opaque token.

    The address is the only identifier available here: the token being tried is exactly what is
    not to be trusted, and keying on it would give every guess its own fresh allowance.
    """
    config = get_rate_limit_config()
    await enforce(
        limiter,
        scope=scope,
        identifiers={"ip": client_address(request)},
        max_attempts=config.token_max_attempts,
        window=timedelta(minutes=config.token_window_minutes),
    )


#: Told apart from a wrong code so the sign-in form knows to ask for one. It says only that the
#: account has a second factor, which the caller has already proved the first factor of.
TOTP_REQUIRED_DETAIL = "totp_required"
INVALID_TOTP_DETAIL = "invalid_totp_code"


async def _enforce_totp_limit(
    limiter: RateLimiter, request: Request, *, account: str, scope: str = "totp"
) -> None:
    """Caps the routes that check a six-digit code.

    Each of them counts against its own scope: a reader setting an authenticator up types the
    wrong code often enough, and spending the sign-in allowance on it would lock them out of the
    account they are in the middle of protecting.
    """
    config = get_rate_limit_config()
    await enforce(
        limiter,
        scope=scope,
        identifiers={"ip": client_address(request), "account": account},
        max_attempts=config.totp_max_attempts,
        window=timedelta(minutes=config.totp_window_minutes),
    )


def _second_factor(payload: SecondFactorFields) -> SecondFactor:
    return SecondFactor(code=payload.totp_code, recovery_code=payload.recovery_code)


def _totp_failure(exc: Exception) -> HTTPException:
    detail = TOTP_REQUIRED_DETAIL if isinstance(exc, TotpRequiredError) else INVALID_TOTP_DETAIL
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def _issue_token_pair(session: AsyncSession, user_id: UUID) -> TokenPairResponse:
    access_token = create_access_token(user_id)
    refresh_token = await issue_refresh_token(session, user_id)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/onboarding/admin",
    response_model=TokenPairResponse,
    status_code=status.HTTP_201_CREATED,
)
async def onboard_admin(
    payload: OnboardingAdminRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
    instance_count = await session.scalar(select(func.count()).select_from(Instance))
    if instance_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    instance_config = get_instance_config()
    instance = Instance(
        max_accounts=payload.max_accounts or instance_config.max_accounts,
        disk_quota_mb=payload.disk_quota_mb or instance_config.account_quota_mb,
    )
    session.add(instance)
    await session.flush()

    user = User(
        instance_id=instance.id,
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=Role.ADMIN,
    )
    session.add(user)
    await session.commit()

    return await _issue_token_pair(session, user.id)


def _to_invitation_response(invitation: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        expires_at=invitation.expires_at,
    )


async def _current_instance(session: AsyncSession) -> Instance:
    instance = await session.scalar(select(Instance))
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return instance


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: InvitationRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> InvitationResponse:
    instance = await _current_instance(session)
    try:
        invitation = await invite_member(session, instance, email=payload.email, role=payload.role)
    except EmailAlreadyTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc
    except InstanceFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="the instance has no seat left",
        ) from exc
    except SsoSubjectMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this address is already linked to another provider account",
        ) from exc
    return _to_invitation_response(invitation)


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[InvitationResponse]:
    instance = await _current_instance(session)
    invitations = await list_pending_invitations(session, instance.id)
    return [_to_invitation_response(invitation) for invitation in invitations]


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invitation(
    invitation_id: UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    instance = await _current_instance(session)
    try:
        await revoke_invitation(session, instance.id, invitation_id)
    except InvalidInvitationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.post(
    "/invitations/accept",
    response_model=TokenPairResponse,
    status_code=status.HTTP_201_CREATED,
)
async def accept_invitation_route(
    payload: InvitationAcceptRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
    """Unauthenticated on purpose: the token is the only credential the invitee has yet."""
    try:
        user = await accept_invitation(
            session, payload.token, username=payload.username, password=payload.password
        )
    except InvalidInvitationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    except (EmailAlreadyTakenError, InstanceFullError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc
    return await _issue_token_pair(session, user.id)


@router.post("/auth/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> TokenPairResponse:
    config = get_rate_limit_config()
    await enforce(
        limiter,
        scope="login",
        identifiers={"ip": client_address(request), "email": payload.email.lower()},
        max_attempts=config.login_max_attempts,
        window=timedelta(minutes=config.login_window_minutes),
    )
    user = await session.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if is_totp_enabled(user):
        await _enforce_totp_limit(limiter, request, account=str(user.id))
        try:
            await verify_second_factor(session, user, _second_factor(payload))
        except (TotpRequiredError, InvalidTotpCodeError) as exc:
            raise _totp_failure(exc) from exc

    return await _issue_token_pair(session, user.id)


@router.post("/auth/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> TokenPairResponse:
    await _enforce_token_guessing_limit(limiter, request, scope="refresh")
    try:
        user_id, refresh_token = await rotate_refresh_token(session, payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    return TokenPairResponse(access_token=create_access_token(user_id), refresh_token=refresh_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await revoke_refresh_token(session, payload.refresh_token)


@router.post("/auth/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_everywhere(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Ends every session of the account, for a device that is gone and cannot be logged out."""
    await revoke_all_refresh_tokens(session, user.id)


@router.post("/auth/magic-link", status_code=status.HTTP_202_ACCEPTED)
async def send_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    config = get_rate_limit_config()
    # Capped by address as well as by mailbox: this route sends a mail on every call, so without
    # it anyone can flood a reader's inbox and fill the token table at no cost.
    await enforce(
        limiter,
        scope="magic-link",
        identifiers={"ip": client_address(request), "email": payload.email.lower()},
        max_attempts=config.magic_link_max_attempts,
        window=timedelta(minutes=config.magic_link_window_minutes),
    )
    await request_magic_link(session, payload.email, payload.purpose)


@router.post("/auth/magic-link/verify", response_model=TokenPairResponse)
async def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> TokenPairResponse:
    await _enforce_token_guessing_limit(limiter, request, scope="magic-link-verify")
    try:
        user_id = await verify_magic_link_token(
            session, payload.token, second_factor=_second_factor(payload)
        )
    except InvalidMagicLinkTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    except (TotpRequiredError, InvalidTotpCodeError) as exc:
        raise _totp_failure(exc) from exc
    return await _issue_token_pair(session, user_id)


@router.post("/auth/password-reset", response_model=TokenPairResponse)
async def reset_forgotten_password(
    payload: PasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> TokenPairResponse:
    """Unauthenticated on purpose: the magic-link token is the credential of a reader locked out."""
    await _enforce_token_guessing_limit(limiter, request, scope="password-reset")
    try:
        user_id = await reset_password(
            session,
            payload.token,
            payload.new_password,
            second_factor=_second_factor(payload),
        )
    except InvalidMagicLinkTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    except (TotpRequiredError, InvalidTotpCodeError) as exc:
        raise _totp_failure(exc) from exc
    return await _issue_token_pair(session, user_id)


async def _read_sso_instance(session: AsyncSession) -> tuple[Instance, SsoConfiguration]:
    instance = await session.scalar(select(Instance))
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        return instance, read_sso_configuration(instance)
    except SsoNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


async def _discover_or_400(
    issuer: str, transport: httpx.AsyncBaseTransport | None
) -> OidcDiscoveryDocument:
    try:
        return await discover(issuer, transport=transport)
    except InsecureIssuerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="the configured OIDC issuer is not an https URL",
        ) from exc


@router.get("/auth/sso/login")
async def sso_login(
    session: AsyncSession = Depends(get_db_session),
    transport: httpx.AsyncBaseTransport | None = Depends(get_oidc_transport),
) -> RedirectResponse:
    _, sso = await _read_sso_instance(session)
    document = await _discover_or_400(sso.issuer, transport)
    state, nonce = await start_login_attempt(session)
    authorize_url = build_authorize_url(
        document,
        client_id=sso.client_id,
        redirect_uri=sso.redirect_uri,
        state=state,
        nonce=nonce,
    )
    return RedirectResponse(authorize_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.post("/auth/sso/callback", response_model=TokenPairResponse)
async def sso_callback(
    payload: SsoCallbackRequest,
    session: AsyncSession = Depends(get_db_session),
    transport: httpx.AsyncBaseTransport | None = Depends(get_oidc_transport),
) -> TokenPairResponse:
    instance, sso = await _read_sso_instance(session)
    try:
        nonce = await consume_login_attempt(session, payload.state)
    except InvalidSsoLoginAttemptError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc

    document = await _discover_or_400(sso.issuer, transport)
    tokens = await exchange_code_for_tokens(
        document,
        client_id=sso.client_id,
        client_secret=decrypt_secret(sso.client_secret_encrypted),
        redirect_uri=sso.redirect_uri,
        code=payload.code,
        transport=transport,
    )
    id_token = tokens.get("id_token")
    if not isinstance(id_token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="the provider returned no id_token",
        )
    try:
        claims = verify_id_token(
            id_token,
            jwks=await fetch_jwks(document, transport=transport),
            issuer=document.issuer,
            client_id=sso.client_id,
            nonce=nonce,
        )
    except InvalidIdTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc

    email = claims.get("email")
    if not email:
        # Some providers keep the address out of the id_token; the subject still comes from the
        # signed claims, so /userinfo only ever fills in the label, never the identity.
        userinfo = await fetch_userinfo(
            document, access_token=tokens["access_token"], transport=transport
        )
        email = userinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="the provider returned no email address",
        )

    try:
        user = await get_or_create_sso_user(
            session, instance, sub=str(claims["sub"]), email=str(email)
        )
    except InstanceFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="the instance has no seat left",
        ) from exc
    except SsoSubjectMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this address is already linked to another provider account",
        ) from exc
    return await _issue_token_pair(session, user.id)


async def _to_me_response(session: AsyncSession, user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
        password_set=user.password_hash is not None,
        totp_enabled=is_totp_enabled(user),
        recovery_codes_left=await count_unused_recovery_codes(session, user),
        theme=user.theme,
        orbit_position=user.orbit_position,
        font_base_size=user.font_base_size,
        preferred_language=user.preferred_language,
        ai_provider=user.ai_provider,
        ai_endpoint_url=user.ai_endpoint_url,
        ai_model=user.ai_model,
        ai_api_key_set=user.ai_api_key_encrypted is not None,
        translation_provider=user.translation_provider,
        translation_api_key_set=user.translation_api_key_encrypted is not None,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    return await _to_me_response(session, user)


@router.get("/me/export", response_model=AccountExportResponse)
async def export_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AccountExportResponse:
    return await export_account(session, user)


@router.post("/me/password", response_model=TokenPairResponse)
async def change_my_password(
    payload: PasswordChangeRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> TokenPairResponse:
    """Changes the password and hands back a fresh pair, the old sessions having just been ended.

    Capped like a sign-in: a stolen access token expires on its own, but guessing the password
    behind it turns a window of minutes into a lasting hold on the account.
    """
    config = get_rate_limit_config()
    await enforce(
        limiter,
        scope="password-change",
        identifiers={"ip": client_address(request), "user": str(user.id)},
        max_attempts=config.login_max_attempts,
        window=timedelta(minutes=config.login_window_minutes),
    )
    try:
        await change_password(
            session,
            user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    return await _issue_token_pair(session, user.id)


@router.post(
    "/me/totp/enrolment",
    response_model=TotpEnrolmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_totp_enrolment(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TotpEnrolmentResponse:
    """Draws a secret for an authenticator to store; nothing is switched on until it is confirmed."""
    try:
        enrolment = await begin_enrolment(session, user)
    except TotpAlreadyEnabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="two-factor sign-in is already on for this account",
        ) from exc
    return TotpEnrolmentResponse(secret=enrolment.secret, otpauth_uri=enrolment.otpauth_uri)


@router.post("/me/totp", response_model=TotpRecoveryCodesResponse)
async def confirm_totp_enrolment(
    payload: TotpConfirmRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> TotpRecoveryCodesResponse:
    """Turns the second factor on, against a code the authenticator has just produced.

    The recovery codes come back here and nowhere else. Without this confirmation step an
    authenticator set up against the wrong secret would lock the account out with no way back.
    """
    await _enforce_totp_limit(limiter, request, account=str(user.id), scope="totp-enrolment")
    try:
        codes = await confirm_enrolment(session, user, payload.code)
    except TotpAlreadyEnabledError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc
    except TotpNotEnrolledError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="start an enrolment before confirming it",
        ) from exc
    except InvalidTotpCodeError as exc:
        raise _totp_failure(exc) from exc
    return TotpRecoveryCodesResponse(recovery_codes=codes)


@router.post("/me/totp/recovery-codes", response_model=TotpRecoveryCodesResponse)
async def renew_recovery_codes(
    payload: TotpConfirmRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> TotpRecoveryCodesResponse:
    """Replaces the whole set, against a live code: the old ones stop working straight away."""
    await _enforce_totp_limit(limiter, request, account=str(user.id), scope="totp-enrolment")
    try:
        await verify_second_factor(session, user, SecondFactor(code=payload.code))
        codes = await regenerate_recovery_codes(session, user)
    except TotpNotEnrolledError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc
    except (TotpRequiredError, InvalidTotpCodeError) as exc:
        raise _totp_failure(exc) from exc
    return TotpRecoveryCodesResponse(recovery_codes=codes)


@router.delete("/me/totp", status_code=status.HTTP_204_NO_CONTENT)
async def disable_my_totp(
    payload: TotpDisableRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    """Turns the second factor off, and asks the reader to prove themselves again first.

    An access token alone must not be enough: it is exactly what someone who walked up to an
    unlocked screen has, and removing the second factor is the one action that undoes the
    protection for every sign-in afterwards.
    """
    if not is_totp_enabled(user):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)

    await _enforce_totp_limit(limiter, request, account=str(user.id), scope="totp-disable")
    if user.password_hash is not None:
        if not (payload.password and verify_password(payload.password, user.password_hash)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    else:
        # An SSO or magic-link account has no password to give; the authenticator it is about to
        # give up is the only thing left to prove with.
        try:
            await verify_second_factor(
                session,
                user,
                SecondFactor(code=payload.totp_code, recovery_code=payload.recovery_code),
            )
        except (TotpRequiredError, InvalidTotpCodeError) as exc:
            raise _totp_failure(exc) from exc

    await disable_totp(session, user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    payload: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if payload.confirm_email.lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="the confirmation address does not match this account",
        )
    if user.password_hash is not None and not (
        payload.password and verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        await delete_account(session, user.id)
    except LastAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="the last admin of the instance cannot delete their account",
        ) from exc


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """An admin removing somebody else's account; their own goes through DELETE /me."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="use DELETE /me to delete your own account",
        )
    target = await session.get(User, user_id)
    if target is None or target.instance_id != admin.instance_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        await delete_account(session, user_id)
    except LastAdminError as exc:  # pragma: no cover - an admin cannot be the last one here
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc


@router.patch("/me", response_model=MeResponse)
async def update_me(
    payload: MeUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MeResponse:
    secret_fields = {"ai_api_key", "translation_api_key"}
    updates = payload.model_dump(exclude_unset=True, exclude=secret_fields)
    for field, value in updates.items():
        setattr(user, field, value)

    # An empty string is what a cleared form field sends; treat it as "remove the key" rather
    # than storing the encryption of nothing.
    if "ai_api_key" in payload.model_fields_set:
        user.ai_api_key_encrypted = (
            encrypt_secret(payload.ai_api_key) if payload.ai_api_key else None
        )
    if "translation_api_key" in payload.model_fields_set:
        user.translation_api_key_encrypted = (
            encrypt_secret(payload.translation_api_key) if payload.translation_api_key else None
        )

    await session.commit()
    return await _to_me_response(session, user)
