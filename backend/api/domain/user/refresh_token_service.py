from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import InvalidRefreshTokenError
from api.domain.user.models import RefreshToken
from api.technical.auth.tokens import generate_opaque_token, hash_token
from config.auth import get_auth_config


async def issue_refresh_token(
    session: AsyncSession, user_id: UUID, *, family_id: UUID | None = None
) -> str:
    """Issues a refresh token, in a new family unless it continues an existing login."""
    raw_token = generate_opaque_token()
    config = get_auth_config()
    session.add(
        RefreshToken(
            user_id=user_id,
            token=hash_token(raw_token),
            family_id=family_id or uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=config.refresh_token_ttl_days),
        )
    )
    await session.commit()
    return raw_token


async def rotate_refresh_token(session: AsyncSession, raw_token: str) -> tuple[UUID, str]:
    """Consumes a refresh token and issues its successor, returning the user and the new token.

    A token is single-use: without rotation, one stolen token stays valid for the whole TTL and
    nothing ever reveals the theft. A token presented after it was rotated away is therefore either
    a replay or a copy, and the whole family — that one login's chain — is revoked, which logs that
    session out on both the thief's side and the reader's while leaving their other devices alone.
    """
    stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token == hash_token(raw_token))
    )
    if stored is None:
        raise InvalidRefreshTokenError
    if stored.revoked_at is not None:
        await _revoke_family(session, stored.family_id)
        raise InvalidRefreshTokenError
    if stored.expires_at < datetime.now(UTC):
        raise InvalidRefreshTokenError

    stored.revoked_at = datetime.now(UTC)
    successor = await issue_refresh_token(session, stored.user_id, family_id=stored.family_id)
    return stored.user_id, successor


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> None:
    stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token == hash_token(raw_token))
    )
    if stored is None:
        return
    await _revoke_family(session, stored.family_id)


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: UUID) -> None:
    """Ends every session of an account — what a lost device or a changed password calls for."""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


async def _revoke_family(session: AsyncSession, family_id: UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
