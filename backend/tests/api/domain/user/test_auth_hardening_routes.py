from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import httpx
import pyotp
import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.user.models import Instance, User
from api.main import app
from config.database import get_engine
from config.email import EmailConfig
from config.rate_limit import get_rate_limit_config

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _onboard(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert response.status_code == 201
    tokens: dict[str, str] = response.json()
    return tokens


async def _enable_totp(client: httpx.AsyncClient, tokens: dict[str, str]) -> str:
    enrolment = await client.post("/me/totp/enrolment", headers=_auth(tokens))
    secret: str = enrolment.json()["secret"]
    confirmed = await client.post(
        "/me/totp", headers=_auth(tokens), json={"code": pyotp.TOTP(secret).now()}
    )
    assert confirmed.status_code == 200
    async with async_sessionmaker(get_engine())() as session:
        await session.execute(update(User).values(totp_last_used_step=None))
        await session.commit()
    return secret


async def _request_link(client: httpx.AsyncClient, raw_token: str, purpose: str) -> None:
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
        patch("api.domain.user.magic_link_service.generate_opaque_token", return_value=raw_token),
    ):
        response = await client.post(
            "/auth/magic-link", json={"email": ADMIN_PAYLOAD["email"], "purpose": purpose}
        )
    assert response.status_code == 202


async def test_a_reset_link_is_refused_by_the_sign_in_route(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    await _request_link(client, "reset-token", "password_reset")

    response = await client.post("/auth/magic-link/verify", json={"token": "reset-token"})

    assert response.status_code == 401


async def test_a_sign_in_link_is_refused_by_the_password_reset_route(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _request_link(client, "signin-token", "sign_in")

    response = await client.post(
        "/auth/password-reset",
        json={"token": "signin-token", "new_password": "another-horse-battery-staple"},
    )

    assert response.status_code == 401


async def test_wrong_codes_on_a_magic_link_are_capped_per_account(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)
    await _request_link(client, "the-raw-token", "sign_in")
    allowance = get_rate_limit_config().totp_max_attempts

    statuses = [
        (
            await client.post(
                "/auth/magic-link/verify",
                json={"token": "the-raw-token", "totp_code": "000000"},
            )
        ).status_code
        for _ in range(allowance + 1)
    ]

    assert statuses[:allowance] == [401] * allowance
    assert statuses[-1] == 429


async def test_wrong_codes_on_a_password_reset_share_the_account_allowance(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)
    await _enable_totp(client, tokens)
    await _request_link(client, "reset-token", "password_reset")
    allowance = get_rate_limit_config().totp_max_attempts

    statuses = [
        (
            await client.post(
                "/auth/password-reset",
                json={
                    "token": "reset-token",
                    "new_password": "another-horse-battery-staple",
                    "totp_code": "000000",
                },
            )
        ).status_code
        for _ in range(allowance + 1)
    ]

    assert statuses[-1] == 429


async def test_signing_in_with_the_email_in_another_case_works(client: httpx.AsyncClient) -> None:
    await _onboard(client)

    response = await client.post(
        "/auth/login",
        json={"email": "ADMIN@Example.com", "password": ADMIN_PAYLOAD["password"]},
    )

    assert response.status_code == 200


async def test_onboarding_stores_the_email_in_lowercase(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/onboarding/admin", json={**ADMIN_PAYLOAD, "email": "Admin@Example.COM"}
    )
    tokens = response.json()

    me = await client.get("/me", headers=_auth(tokens))

    assert me.json()["email"] == "admin@example.com"


async def test_a_magic_link_is_sent_whatever_the_case_the_reader_typed(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)

    with patch(
        "api.domain.user.magic_link_service.send_email", new_callable=AsyncMock
    ) as mock_send:
        await client.post("/auth/magic-link", json={"email": "ADMIN@EXAMPLE.COM"})

    mock_send.assert_awaited_once()


async def test_the_database_refuses_two_accounts_differing_only_by_case(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    async with async_sessionmaker(get_engine())() as session:
        instance = (await session.scalars(select(Instance))).one()
        session.add(User(instance_id=instance.id, email="ADMIN@example.com", username="twin"))
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("https://lumia.example.com", "https://lumia.example.com"),
        ("https://lumia.example.com/", "https://lumia.example.com"),
        ("https://a.example.com, https://b.example.com", "https://a.example.com"),
        (" ,https://b.example.com/", "https://b.example.com"),
    ],
)
def test_the_frontend_url_may_be_a_list_and_the_first_entry_is_used(
    configured: str, expected: str
) -> None:
    config = EmailConfig(
        smtp_host="h",
        smtp_username="u",
        smtp_password="p",
        smtp_from_address="a@b.c",
        frontend_url=configured,
    )

    assert config.frontend_base_url == expected


async def test_the_magic_link_mail_uses_the_first_frontend_origin(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    config = EmailConfig(
        smtp_host="h",
        smtp_username="u",
        smtp_password="p",
        smtp_from_address="a@b.c",
        frontend_url="https://a.example.com,https://b.example.com",
    )

    with (
        patch("api.domain.user.magic_link_service.get_email_config", return_value=config),
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock) as mock_send,
    ):
        await client.post("/auth/magic-link", json={"email": ADMIN_PAYLOAD["email"]})

    assert mock_send.await_args is not None
    assert "https://a.example.com/login?magic_token=" in mock_send.await_args.kwargs["body"]


async def test_a_login_for_an_unknown_account_still_spends_a_password_verification(
    client: httpx.AsyncClient,
) -> None:
    with patch("api.domain.user.routes.spend_verification_time") as decoy:
        response = await client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "whatever-it-is"}
        )

    assert response.status_code == 401
    decoy.assert_called_once_with("whatever-it-is")


async def test_a_login_for_a_known_account_does_not_use_the_decoy(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)

    with patch("api.domain.user.routes.spend_verification_time") as decoy:
        response = await client.post(
            "/auth/login",
            json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
        )

    assert response.status_code == 200
    decoy.assert_not_called()
