from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.models import Instance, MagicLinkToken, RefreshToken, User
from config.database import get_engine
from config.maintenance import get_maintenance_config
from worker.domain.maintenance.purge_tokens import purge_expired_tokens

GRACE = timedelta(days=get_maintenance_config().token_purge_grace_days)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="reader")
    session.add(user)
    await session.commit()
    return user


async def _add_tokens(session: AsyncSession, user: User, *, expires_at: datetime) -> None:
    session.add(RefreshToken(user_id=user.id, token=f"refresh-{uuid4()}", expires_at=expires_at))
    session.add(MagicLinkToken(user_id=user.id, token=f"magic-{uuid4()}", expires_at=expires_at))
    await session.commit()


async def _counts(session: AsyncSession) -> tuple[int, int]:
    refresh = await session.scalar(select(func.count()).select_from(RefreshToken))
    magic = await session.scalar(select(func.count()).select_from(MagicLinkToken))
    return refresh or 0, magic or 0


async def test_tokens_expired_long_ago_are_deleted(session: AsyncSession) -> None:
    """Nothing ever removed them, so both tables grew for the lifetime of the instance."""
    user = await _create_user(session)
    await _add_tokens(session, user, expires_at=datetime.now(UTC) - GRACE - timedelta(days=1))

    purged = await purge_expired_tokens({})

    assert purged == 2
    assert await _counts(session) == (0, 0)


async def test_a_live_token_survives(session: AsyncSession) -> None:
    user = await _create_user(session)
    await _add_tokens(session, user, expires_at=datetime.now(UTC) + timedelta(days=1))

    assert await purge_expired_tokens({}) == 0
    assert await _counts(session) == (1, 1)


async def test_a_token_within_the_grace_period_survives(session: AsyncSession) -> None:
    """Just-lapsed is worth recognising as expired rather than as never issued."""
    user = await _create_user(session)
    await _add_tokens(session, user, expires_at=datetime.now(UTC) - timedelta(minutes=5))

    assert await purge_expired_tokens({}) == 0
    assert await _counts(session) == (1, 1)


async def test_the_purge_leaves_the_live_tokens_of_the_same_reader(session: AsyncSession) -> None:
    user = await _create_user(session)
    await _add_tokens(session, user, expires_at=datetime.now(UTC) - GRACE - timedelta(days=1))
    await _add_tokens(session, user, expires_at=datetime.now(UTC) + timedelta(days=1))

    assert await purge_expired_tokens({}) == 2
    assert await _counts(session) == (1, 1)


async def test_purging_an_empty_database_is_a_no_op(session: AsyncSession) -> None:
    assert await purge_expired_tokens({}) == 0
