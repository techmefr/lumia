from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.dependencies import get_current_user, require_admin
from api.domain.user.exceptions import (
    EmailAlreadyTakenError,
    InstanceFullError,
    InvalidInvitationError,
    InvalidMagicLinkTokenError,
    InvalidRefreshTokenError,
    InvalidSsoLoginAttemptError,
    SsoNotConfiguredError,
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
from api.domain.user.refresh_token_service import (
    issue_refresh_token,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from api.domain.user.schemas import (
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
    RefreshRequest,
    SsoCallbackRequest,
    TokenPairResponse,
)
from api.domain.user.sso_service import (
    SsoConfiguration,
    get_or_create_sso_user,
    read_sso_configuration,
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

router = APIRouter()


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

    instance = Instance(max_accounts=payload.max_accounts, disk_quota_mb=payload.disk_quota_mb)
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
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return await _issue_token_pair(session, user.id)


@router.post("/auth/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
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
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await request_magic_link(session, payload.email)


@router.post("/auth/magic-link/verify", response_model=TokenPairResponse)
async def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
    try:
        user_id = await verify_magic_link_token(session, payload.token)
    except InvalidMagicLinkTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
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
    return await _issue_token_pair(session, user.id)


def _to_me_response(user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        role=user.role,
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
async def get_me(user: User = Depends(get_current_user)) -> MeResponse:
    return _to_me_response(user)


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
    return _to_me_response(user)
