from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.user.exceptions import InvalidRefreshTokenError
from api.domain.user.models import RefreshToken
from api.technical.auth.tokens import generate_opaque_token, hash_token
from config.auth import get_auth_config


async def issue_refresh_token(session: AsyncSession, user_id: UUID) -> str:
    raw_token = generate_opaque_token()
    config = get_auth_config()
    session.add(
        RefreshToken(
            user_id=user_id,
            token=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(days=config.refresh_token_ttl_days),
        )
    )
    await session.commit()
    return raw_token


async def get_user_id_for_refresh_token(session: AsyncSession, raw_token: str) -> UUID:
    stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token == hash_token(raw_token))
    )
    if stored is None or stored.expires_at < datetime.now(UTC):
        raise InvalidRefreshTokenError
    return stored.user_id


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> None:
    await session.execute(delete(RefreshToken).where(RefreshToken.token == hash_token(raw_token)))
    await session.commit()
