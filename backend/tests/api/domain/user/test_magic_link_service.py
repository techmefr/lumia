from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.user.exceptions import InvalidMagicLinkTokenError
from api.domain.user.magic_link_service import request_magic_link, verify_magic_link_token
from api.domain.user.models import Instance, MagicLinkToken, ReadingLang, User
from api.technical.auth.tokens import hash_token
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(
    session: AsyncSession, email: str, preferred_language: ReadingLang = ReadingLang.FR
) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email=email,
        username="member",
        password_hash=None,
        preferred_language=preferred_language,
    )
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


async def _send_magic_link(session: AsyncSession, email: str) -> AsyncMock:
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock) as mock_send,
        patch(
            "api.domain.user.magic_link_service.generate_opaque_token",
            return_value="the-raw-token",
        ),
    ):
        await request_magic_link(session, email)
    return mock_send


async def test_request_magic_link_writes_in_french_for_a_french_account(
    session: AsyncSession,
) -> None:
    await _create_user(session, "fr@example.com", ReadingLang.FR)

    mock_send = await _send_magic_link(session, "fr@example.com")

    assert mock_send.await_args is not None
    assert mock_send.await_args.kwargs["subject"] == "Votre lien de connexion Lumia"
    assert "vous connecter" in mock_send.await_args.kwargs["body"]


async def test_request_magic_link_writes_in_english_for_an_english_account(
    session: AsyncSession,
) -> None:
    await _create_user(session, "en@example.com", ReadingLang.EN)

    mock_send = await _send_magic_link(session, "en@example.com")

    assert mock_send.await_args is not None
    assert mock_send.await_args.kwargs["subject"] == "Your Lumia sign-in link"
    assert "sign in" in mock_send.await_args.kwargs["body"].lower()


async def test_request_magic_link_falls_back_to_english_for_an_untranslated_language(
    session: AsyncSession,
) -> None:
    await _create_user(session, "mg@example.com", ReadingLang.MG)

    mock_send = await _send_magic_link(session, "mg@example.com")

    assert mock_send.await_args is not None
    assert mock_send.await_args.kwargs["subject"] == "Your Lumia sign-in link"


async def test_request_magic_link_keeps_the_url_in_both_parts_whatever_the_language(
    session: AsyncSession,
) -> None:
    await _create_user(session, "en@example.com", ReadingLang.EN)

    mock_send = await _send_magic_link(session, "en@example.com")

    assert mock_send.await_args is not None
    expected_url = "http://localhost:8080/login?magic_token=the-raw-token"
    assert expected_url in mock_send.await_args.kwargs["body"]
    assert f'href="{expected_url}"' in mock_send.await_args.kwargs["html_body"]


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


async def test_asking_for_a_new_link_retires_the_previous_one(session: AsyncSession) -> None:
    """Several live links mean several windows an old mail can still be replayed through."""
    await _create_user(session, "user@example.com")
    for raw_token in ("first-token", "second-token"):
        with (
            patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
            patch(
                "api.domain.user.magic_link_service.generate_opaque_token",
                return_value=raw_token,
            ),
        ):
            await request_magic_link(session, "user@example.com")

    with pytest.raises(InvalidMagicLinkTokenError):
        await verify_magic_link_token(session, "first-token")


async def test_the_newest_link_is_the_one_that_works(session: AsyncSession) -> None:
    user = await _create_user(session, "user@example.com")
    for raw_token in ("first-token", "second-token"):
        with (
            patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
            patch(
                "api.domain.user.magic_link_service.generate_opaque_token",
                return_value=raw_token,
            ),
        ):
            await request_magic_link(session, "user@example.com")

    assert await verify_magic_link_token(session, "second-token") == user.id


async def test_asking_for_a_link_leaves_another_reader_s_link_alone(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, "first@example.com")
    await _create_user(session, "second@example.com")
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
        patch(
            "api.domain.user.magic_link_service.generate_opaque_token",
            return_value="theirs",
        ),
    ):
        await request_magic_link(session, "first@example.com")
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
        patch("api.domain.user.magic_link_service.generate_opaque_token", return_value="mine"),
    ):
        await request_magic_link(session, "second@example.com")

    assert await verify_magic_link_token(session, "theirs") == user.id
