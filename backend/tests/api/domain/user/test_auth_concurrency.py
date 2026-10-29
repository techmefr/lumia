import asyncio
from collections.abc import AsyncIterator, Awaitable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pyotp
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import (
    InvalidMagicLinkTokenError,
    InvalidRefreshTokenError,
    InvalidTotpCodeError,
)
from api.domain.user.magic_link_service import verify_magic_link_token
from api.domain.user.models import (
    Instance,
    MagicLinkPurpose,
    MagicLinkToken,
    RecoveryCode,
    RefreshToken,
    User,
)
from api.domain.user.refresh_token_service import issue_refresh_token, rotate_refresh_token
from api.domain.user.totp_service import (
    SecondFactor,
    begin_enrolment,
    confirm_enrolment,
    verify_second_factor,
)
from api.technical.auth.tokens import hash_token
from api.technical.auth.totp import TotpEnrolment
from config.database import get_engine


@pytest.fixture
async def sessions(db_schema: None) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield async_sessionmaker(get_engine(), expire_on_commit=False)


async def _create_user(factory: async_sessionmaker[AsyncSession]) -> User:
    async with factory() as session:
        instance = Instance(max_accounts=10, disk_quota_mb=1000)
        session.add(instance)
        await session.flush()
        user = User(
            instance_id=instance.id,
            email=f"{uuid4()}@example.com",
            username="reader",
            password_hash=None,
        )
        session.add(user)
        await session.commit()
        return user


async def _race(*attempts: Awaitable[object]) -> list[object]:
    return list(await asyncio.gather(*attempts, return_exceptions=True))


async def test_a_magic_link_spent_twice_at_once_signs_in_exactly_once(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(sessions)
    async with sessions() as session:
        session.add(
            MagicLinkToken(
                user_id=user.id,
                token=hash_token("raced"),
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        await session.commit()

    async def attempt() -> object:
        async with sessions() as session:
            return await verify_magic_link_token(session, "raced")

    outcomes = await _race(*(attempt() for _ in range(5)))

    assert sum(1 for outcome in outcomes if outcome == user.id) == 1
    assert sum(isinstance(outcome, InvalidMagicLinkTokenError) for outcome in outcomes) == 4


async def test_a_refresh_token_rotated_twice_at_once_yields_one_successor(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(sessions)
    async with sessions() as session:
        raw_token = await issue_refresh_token(session, user.id)

    async def attempt() -> object:
        async with sessions() as session:
            return await rotate_refresh_token(session, raw_token)

    outcomes = await _race(*(attempt() for _ in range(5)))

    successes = [outcome for outcome in outcomes if isinstance(outcome, tuple)]
    assert len(successes) == 1
    assert sum(isinstance(outcome, InvalidRefreshTokenError) for outcome in outcomes) == 4


async def test_a_replayed_refresh_token_revokes_the_family(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(sessions)
    async with sessions() as session:
        raw_token = await issue_refresh_token(session, user.id)
        _, successor = await rotate_refresh_token(session, raw_token)

    async with sessions() as session:
        with pytest.raises(InvalidRefreshTokenError):
            await rotate_refresh_token(session, raw_token)

    async with sessions() as session:
        with pytest.raises(InvalidRefreshTokenError):
            await rotate_refresh_token(session, successor)
        live = await session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
            )
        )
        assert list(live) == []


async def _enrol(
    sessions: async_sessionmaker[AsyncSession], user: User
) -> tuple[TotpEnrolment, list[str]]:
    async with sessions() as session:
        stored = await session.get(User, user.id)
        assert stored is not None
        enrolment = await begin_enrolment(session, stored)
        codes = await confirm_enrolment(session, stored, pyotp.TOTP(enrolment.secret).now())
        stored.totp_last_used_step = None
        await session.commit()
    return enrolment, codes


async def test_a_recovery_code_spent_twice_at_once_works_once(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(sessions)
    _, codes = await _enrol(sessions, user)

    async def attempt() -> object:
        async with sessions() as session:
            stored = await session.get(User, user.id)
            assert stored is not None
            await verify_second_factor(session, stored, SecondFactor(recovery_code=codes[0]))
            return None

    outcomes = await _race(*(attempt() for _ in range(5)))

    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(isinstance(outcome, InvalidTotpCodeError) for outcome in outcomes) == 4
    async with sessions() as session:
        spent = await session.scalars(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_not(None)
            )
        )
        assert len(list(spent)) == 1


async def test_a_totp_code_presented_twice_at_once_is_accepted_once(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(sessions)
    enrolment, _ = await _enrol(sessions, user)
    code = pyotp.TOTP(enrolment.secret).now()

    async def attempt() -> object:
        async with sessions() as session:
            stored = await session.get(User, user.id)
            assert stored is not None
            await verify_second_factor(session, stored, SecondFactor(code=code))
            return None

    outcomes = await _race(*(attempt() for _ in range(5)))

    assert sum(outcome is None for outcome in outcomes) == 1
    assert sum(isinstance(outcome, InvalidTotpCodeError) for outcome in outcomes) == 4


async def test_a_reset_link_cannot_open_a_session(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(sessions)
    async with sessions() as session:
        session.add(
            MagicLinkToken(
                user_id=user.id,
                token=hash_token("reset"),
                purpose=MagicLinkPurpose.PASSWORD_RESET,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        await session.commit()

    async with sessions() as session:
        with pytest.raises(InvalidMagicLinkTokenError):
            await verify_magic_link_token(session, "reset")


async def test_a_sign_in_link_cannot_reset_a_password(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    user = await _create_user(sessions)
    async with sessions() as session:
        session.add(
            MagicLinkToken(
                user_id=user.id,
                token=hash_token("signin"),
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        await session.commit()

    async with sessions() as session:
        with pytest.raises(InvalidMagicLinkTokenError):
            await verify_magic_link_token(
                session, "signin", purpose=MagicLinkPurpose.PASSWORD_RESET
            )

    async with sessions() as session:
        assert await verify_magic_link_token(session, "signin") == user.id
