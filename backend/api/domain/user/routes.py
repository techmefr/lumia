from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import InvalidMagicLinkTokenError, InvalidRefreshTokenError
from api.domain.user.magic_link_service import request_magic_link, verify_magic_link_token
from api.domain.user.models import Instance, Role, User
from api.domain.user.refresh_token_service import (
    get_user_id_for_refresh_token,
    issue_refresh_token,
    revoke_refresh_token,
)
from api.domain.user.schemas import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    OnboardingAdminRequest,
    RefreshRequest,
    TokenPairResponse,
)
from api.technical.auth.hashing import hash_password, verify_password
from api.technical.auth.jwt import create_access_token
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


@router.post("/auth/refresh", response_model=AccessTokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AccessTokenResponse:
    try:
        user_id = await get_user_id_for_refresh_token(session, payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    return AccessTokenResponse(access_token=create_access_token(user_id))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await revoke_refresh_token(session, payload.refresh_token)


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
