from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import InvalidSsoLoginAttemptError
from api.domain.user.models import OidcLoginAttempt
from api.domain.user.oidc_login_service import consume_login_attempt, start_login_attempt
from api.technical.auth.tokens import hash_token
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def test_starting_a_login_returns_a_state_and_a_nonce(session: AsyncSession) -> None:
    state, nonce = await start_login_attempt(session)

    assert state
    assert nonce
    assert state != nonce


async def test_only_the_hash_of_the_state_is_stored(session: AsyncSession) -> None:
    """A dump of the table must not hand out states an attacker can present."""
    state, _ = await start_login_attempt(session)

    stored = (await session.scalars(select(OidcLoginAttempt))).one()
    assert stored.state == hash_token(state)


async def test_consuming_returns_the_nonce_of_that_login(session: AsyncSession) -> None:
    state, nonce = await start_login_attempt(session)

    assert await consume_login_attempt(session, state) == nonce


async def test_a_state_cannot_be_consumed_twice(session: AsyncSession) -> None:
    state, _ = await start_login_attempt(session)
    await consume_login_attempt(session, state)

    with pytest.raises(InvalidSsoLoginAttemptError):
        await consume_login_attempt(session, state)


async def test_consuming_a_state_nobody_issued_is_refused(session: AsyncSession) -> None:
    with pytest.raises(InvalidSsoLoginAttemptError):
        await consume_login_attempt(session, "forged-state")


async def test_consuming_an_expired_state_is_refused(session: AsyncSession) -> None:
    session.add(
        OidcLoginAttempt(
            state=hash_token("stale-state"),
            nonce="stale-nonce",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    await session.commit()

    with pytest.raises(InvalidSsoLoginAttemptError):
        await consume_login_attempt(session, "stale-state")


async def test_consuming_one_login_leaves_the_others_alone(session: AsyncSession) -> None:
    first, first_nonce = await start_login_attempt(session)
    second, second_nonce = await start_login_attempt(session)

    assert await consume_login_attempt(session, first) == first_nonce
    assert await consume_login_attempt(session, second) == second_nonce
