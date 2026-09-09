from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import InvalidMagicLinkTokenError
from api.domain.user.magic_link_service import request_magic_link, verify_magic_link_token
from api.domain.user.models import Instance, MagicLinkToken, User
from api.technical.auth.tokens import hash_token
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(session: AsyncSession, email: str) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=email, username="member", password_hash=None)
    session.add(user)
    await session.commit()
    return user


async def test_request_magic_link_sends_an_email_for_a_known_address(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, "known@example.com")
    with patch(
        "api.domain.user.magic_link_service.send_email", new_callable=AsyncMock
    ) as mock_send:
        await request_magic_link(session, "known@example.com")

    mock_send.assert_awaited_once()
    assert mock_send.await_args is not None
    assert mock_send.await_args.kwargs["to"] == user.email


async def test_request_magic_link_email_contains_a_clickable_login_url(
    session: AsyncSession,
) -> None:
    await _create_user(session, "known@example.com")
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock) as mock_send,
        patch(
            "api.domain.user.magic_link_service.generate_opaque_token",
            return_value="the-raw-token",
        ),
    ):
        await request_magic_link(session, "known@example.com")

    assert mock_send.await_args is not None
    body = mock_send.await_args.kwargs["body"]
    assert "http://localhost:8080/login?magic_token=the-raw-token" in body


async def test_request_magic_link_does_nothing_for_an_unknown_address(
    session: AsyncSession,
) -> None:
    with patch(
        "api.domain.user.magic_link_service.send_email", new_callable=AsyncMock
    ) as mock_send:
        await request_magic_link(session, "unknown@example.com")

    mock_send.assert_not_awaited()


async def test_verify_magic_link_token_round_trip(session: AsyncSession) -> None:
    user = await _create_user(session, "user@example.com")
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
        patch(
            "api.domain.user.magic_link_service.generate_opaque_token",
            return_value="the-raw-token",
        ),
    ):
        await request_magic_link(session, "user@example.com")

    assert await verify_magic_link_token(session, "the-raw-token") == user.id


async def test_verify_magic_link_token_rejects_an_unknown_token(session: AsyncSession) -> None:
    with pytest.raises(InvalidMagicLinkTokenError):
        await verify_magic_link_token(session, "never-issued")


async def test_verify_magic_link_token_rejects_an_already_used_token(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, "user@example.com")
    session.add(
        MagicLinkToken(
            user_id=user.id,
            token=hash_token("used-token"),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
            used_at=datetime.now(UTC),
        )
    )
    await session.commit()
    with pytest.raises(InvalidMagicLinkTokenError):
        await verify_magic_link_token(session, "used-token")


async def test_verify_magic_link_token_rejects_an_expired_token(session: AsyncSession) -> None:
    user = await _create_user(session, "user@example.com")
    session.add(
        MagicLinkToken(
            user_id=user.id,
            token=hash_token("expired-token"),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    await session.commit()
    with pytest.raises(InvalidMagicLinkTokenError):
        await verify_magic_link_token(session, "expired-token")


async def test_verify_magic_link_token_can_only_be_used_once(session: AsyncSession) -> None:
    user = await _create_user(session, "user@example.com")
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
        patch(
            "api.domain.user.magic_link_service.generate_opaque_token",
            return_value="single-use-token",
        ),
    ):
        await request_magic_link(session, "user@example.com")

    assert await verify_magic_link_token(session, "single-use-token") == user.id
    with pytest.raises(InvalidMagicLinkTokenError):
        await verify_magic_link_token(session, "single-use-token")
