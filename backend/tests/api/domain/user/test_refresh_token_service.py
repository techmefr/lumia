from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import InvalidRefreshTokenError
from api.domain.user.models import Instance, RefreshToken, User
from api.domain.user.refresh_token_service import (
    get_user_id_for_refresh_token,
    issue_refresh_token,
    revoke_refresh_token,
)
from api.technical.auth.tokens import hash_token
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email=f"{uuid4()}@example.com",
        username="member",
        password_hash="irrelevant",
    )
    session.add(user)
    await session.commit()
    return user


async def test_issue_and_verify_round_trip(session: AsyncSession) -> None:
    user = await _create_user(session)
    raw_token = await issue_refresh_token(session, user.id)
    assert await get_user_id_for_refresh_token(session, raw_token) == user.id


async def test_verify_rejects_an_unknown_token(session: AsyncSession) -> None:
    with pytest.raises(InvalidRefreshTokenError):
        await get_user_id_for_refresh_token(session, "unknown-token")


async def test_verify_rejects_an_expired_token(session: AsyncSession) -> None:
    user = await _create_user(session)
    raw_token = "expired-token"
    session.add(
        RefreshToken(
            user_id=user.id,
            token=hash_token(raw_token),
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    await session.commit()
    with pytest.raises(InvalidRefreshTokenError):
        await get_user_id_for_refresh_token(session, raw_token)


async def test_revoke_then_verify_rejects_the_token(session: AsyncSession) -> None:
    user = await _create_user(session)
    raw_token = await issue_refresh_token(session, user.id)
    await revoke_refresh_token(session, raw_token)
    with pytest.raises(InvalidRefreshTokenError):
        await get_user_id_for_refresh_token(session, raw_token)


async def test_revoke_of_an_unknown_token_is_a_no_op(session: AsyncSession) -> None:
    await revoke_refresh_token(session, "never-issued")
