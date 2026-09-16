from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import InvalidCurrentPasswordError
from api.domain.user.models import Instance, MagicLinkToken, RefreshToken, User
from api.domain.user.password_service import change_password, reset_password
from api.domain.user.refresh_token_service import issue_refresh_token
from api.technical.auth.hashing import hash_password, verify_password
from api.technical.auth.tokens import hash_token
from config.database import get_engine

CURRENT_PASSWORD = "correct-horse-battery-staple"
NEW_PASSWORD = "another-horse-battery-staple"


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(session: AsyncSession, *, password: str | None) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email="member@example.com",
        username="member",
        password_hash=hash_password(password) if password else None,
    )
    session.add(user)
    await session.commit()
    return user


async def _live_token_count(session: AsyncSession, user: User) -> int:
    tokens = await session.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    )
    return len(list(tokens))


async def test_change_password_stores_the_new_one_hashed(session: AsyncSession) -> None:
    user = await _create_user(session, password=CURRENT_PASSWORD)

    await change_password(
        session, user, current_password=CURRENT_PASSWORD, new_password=NEW_PASSWORD
    )

    assert user.password_hash is not None
    assert user.password_hash != NEW_PASSWORD
    assert verify_password(NEW_PASSWORD, user.password_hash)


async def test_change_password_refuses_a_wrong_current_password(session: AsyncSession) -> None:
    user = await _create_user(session, password=CURRENT_PASSWORD)

    with pytest.raises(InvalidCurrentPasswordError):
        await change_password(
            session, user, current_password="not-the-one", new_password=NEW_PASSWORD
        )

    assert user.password_hash is not None
    assert verify_password(CURRENT_PASSWORD, user.password_hash)


async def test_change_password_refuses_a_missing_current_password(session: AsyncSession) -> None:
    user = await _create_user(session, password=CURRENT_PASSWORD)

    with pytest.raises(InvalidCurrentPasswordError):
        await change_password(session, user, current_password=None, new_password=NEW_PASSWORD)


async def test_an_account_without_a_password_sets_its_first_one(session: AsyncSession) -> None:
    """An SSO or magic-link account has nothing to prove: asking for it would trap the account."""
    user = await _create_user(session, password=None)

    await change_password(session, user, current_password=None, new_password=NEW_PASSWORD)

    assert user.password_hash is not None
    assert verify_password(NEW_PASSWORD, user.password_hash)


async def test_change_password_ends_every_session(session: AsyncSession) -> None:
    user = await _create_user(session, password=CURRENT_PASSWORD)
    await issue_refresh_token(session, user.id)
    await issue_refresh_token(session, user.id)

    await change_password(
        session, user, current_password=CURRENT_PASSWORD, new_password=NEW_PASSWORD
    )

    assert await _live_token_count(session, user) == 0


async def test_a_refused_change_leaves_the_sessions_alone(session: AsyncSession) -> None:
    user = await _create_user(session, password=CURRENT_PASSWORD)
    await issue_refresh_token(session, user.id)

    with pytest.raises(InvalidCurrentPasswordError):
        await change_password(
            session, user, current_password="not-the-one", new_password=NEW_PASSWORD
        )

    assert await _live_token_count(session, user) == 1


async def _add_magic_link(session: AsyncSession, user: User, raw_token: str) -> None:
    session.add(
        MagicLinkToken(
            user_id=user.id,
            token=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
    )
    await session.commit()


async def test_reset_password_writes_the_new_one_and_names_the_account(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, password=CURRENT_PASSWORD)
    await _add_magic_link(session, user, "reset-token")

    assert await reset_password(session, "reset-token", NEW_PASSWORD) == user.id

    await session.refresh(user)
    assert user.password_hash is not None
    assert verify_password(NEW_PASSWORD, user.password_hash)


async def test_reset_password_ends_every_session(session: AsyncSession) -> None:
    user = await _create_user(session, password=CURRENT_PASSWORD)
    await issue_refresh_token(session, user.id)
    await _add_magic_link(session, user, "reset-token")

    await reset_password(session, "reset-token", NEW_PASSWORD)

    assert await _live_token_count(session, user) == 0
