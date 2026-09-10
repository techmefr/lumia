from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import InvalidRefreshTokenError
from api.domain.user.models import Instance, RefreshToken, User
from api.domain.user.refresh_token_service import (
    issue_refresh_token,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
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


async def _stored(session: AsyncSession, raw_token: str) -> RefreshToken:
    token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token == hash_token(raw_token))
    )
    assert token is not None
    return token


async def test_rotating_returns_the_user_and_a_different_token(session: AsyncSession) -> None:
    user = await _create_user(session)
    raw_token = await issue_refresh_token(session, user.id)

    user_id, successor = await rotate_refresh_token(session, raw_token)

    assert user_id == user.id
    assert successor != raw_token


async def test_the_rotated_token_cannot_be_used_again(session: AsyncSession) -> None:
    user = await _create_user(session)
    raw_token = await issue_refresh_token(session, user.id)
    await rotate_refresh_token(session, raw_token)

    with pytest.raises(InvalidRefreshTokenError):
        await rotate_refresh_token(session, raw_token)


async def test_the_successor_stays_in_the_same_family(session: AsyncSession) -> None:
    user = await _create_user(session)
    raw_token = await issue_refresh_token(session, user.id)
    _, successor = await rotate_refresh_token(session, raw_token)

    assert (await _stored(session, successor)).family_id == (
        await _stored(session, raw_token)
    ).family_id


async def test_replaying_a_rotated_token_kills_the_whole_chain(session: AsyncSession) -> None:
    """A token that comes back after being rotated away is a copy, so the session it belongs to
    is ended on both sides rather than left to the thief."""
    user = await _create_user(session)
    raw_token = await issue_refresh_token(session, user.id)
    _, successor = await rotate_refresh_token(session, raw_token)

    with pytest.raises(InvalidRefreshTokenError):
        await rotate_refresh_token(session, raw_token)

    with pytest.raises(InvalidRefreshTokenError):
        await rotate_refresh_token(session, successor)


async def test_a_replay_leaves_the_other_devices_alone(session: AsyncSession) -> None:
    user = await _create_user(session)
    phone = await issue_refresh_token(session, user.id)
    laptop = await issue_refresh_token(session, user.id)
    await rotate_refresh_token(session, phone)

    with pytest.raises(InvalidRefreshTokenError):
        await rotate_refresh_token(session, phone)

    user_id, _ = await rotate_refresh_token(session, laptop)
    assert user_id == user.id


async def test_rotating_rejects_an_unknown_token(session: AsyncSession) -> None:
    with pytest.raises(InvalidRefreshTokenError):
        await rotate_refresh_token(session, "unknown-token")


async def test_rotating_rejects_an_expired_token(session: AsyncSession) -> None:
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
        await rotate_refresh_token(session, raw_token)


async def test_revoking_marks_the_token_rather_than_deleting_it(session: AsyncSession) -> None:
    """The row has to survive: a revoked token that comes back is what reveals a theft."""
    user = await _create_user(session)
    raw_token = await issue_refresh_token(session, user.id)

    await revoke_refresh_token(session, raw_token)

    assert (await _stored(session, raw_token)).revoked_at is not None
    with pytest.raises(InvalidRefreshTokenError):
        await rotate_refresh_token(session, raw_token)


async def test_revoking_an_unknown_token_is_a_no_op(session: AsyncSession) -> None:
    await revoke_refresh_token(session, "never-issued")


async def test_revoking_everything_ends_every_session_of_the_account(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)
    phone = await issue_refresh_token(session, user.id)
    laptop = await issue_refresh_token(session, user.id)

    await revoke_all_refresh_tokens(session, user.id)

    for raw_token in (phone, laptop):
        with pytest.raises(InvalidRefreshTokenError):
            await rotate_refresh_token(session, raw_token)


async def test_revoking_everything_spares_the_other_accounts(session: AsyncSession) -> None:
    user = await _create_user(session)
    other = await _create_user(session)
    theirs = await issue_refresh_token(session, other.id)

    await revoke_all_refresh_tokens(session, user.id)

    user_id, _ = await rotate_refresh_token(session, theirs)
    assert user_id == other.id
