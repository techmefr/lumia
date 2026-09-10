from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from api.main import app
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


async def _onboard(client: httpx.AsyncClient) -> None:
    assert (await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)).status_code == 201


def _from(address: str) -> dict[str, str]:
    return {"X-Forwarded-For": address}


async def _wrong_password(
    client: httpx.AsyncClient, *, address: str = "203.0.113.1", email: str | None = None
) -> httpx.Response:
    return await client.post(
        "/auth/login",
        json={"email": email or ADMIN_PAYLOAD["email"], "password": "wrong-password"},
        headers=_from(address),
    )


async def test_a_burst_of_wrong_passwords_ends_in_429(client: httpx.AsyncClient) -> None:
    """Argon2 makes each guess slow; nothing made them finite."""
    await _onboard(client)
    allowance = get_rate_limit_config().login_max_attempts

    for _ in range(allowance):
        assert (await _wrong_password(client)).status_code == 401

    refused = await _wrong_password(client)
    assert refused.status_code == 429


async def test_the_refusal_tells_the_caller_when_to_come_back(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    for _ in range(get_rate_limit_config().login_max_attempts + 1):
        response = await _wrong_password(client)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


async def test_a_spent_allowance_also_refuses_the_right_password(
    client: httpx.AsyncClient,
) -> None:
    """A limit that lets the correct password through is no limit: that is what is being guessed."""
    await _onboard(client)
    for _ in range(get_rate_limit_config().login_max_attempts):
        await _wrong_password(client)

    response = await client.post(
        "/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
        headers=_from("203.0.113.1"),
    )

    assert response.status_code == 429


async def test_one_account_being_hammered_leaves_the_others_reachable(
    client: httpx.AsyncClient,
) -> None:
    """Spread over many addresses, the per-account cap is what stops it — and only that account."""
    await _onboard(client)
    for attempt in range(get_rate_limit_config().login_max_attempts + 1):
        await _wrong_password(client, address=f"198.51.100.{attempt}")

    response = await client.post(
        "/auth/login",
        json={"email": "someone-else@example.com", "password": "whatever"},
        headers=_from("198.51.100.200"),
    )

    assert response.status_code == 401


async def test_the_email_allowance_ignores_the_case_of_the_address(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    allowance = get_rate_limit_config().login_max_attempts
    for attempt in range(allowance):
        await _wrong_password(client, address=f"198.51.100.{attempt}", email="ADMIN@example.com")

    refused = await _wrong_password(client, address="198.51.100.250")
    assert refused.status_code == 429


async def test_a_burst_of_magic_links_ends_in_429(client: httpx.AsyncClient) -> None:
    """This route sends a mail on every call: unbounded, it is a mail flood on demand."""
    await _onboard(client)
    allowance = get_rate_limit_config().magic_link_max_attempts

    with patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock) as sent:
        for _ in range(allowance):
            response = await client.post(
                "/auth/magic-link",
                json={"email": ADMIN_PAYLOAD["email"]},
                headers=_from("203.0.113.1"),
            )
            assert response.status_code == 202

        refused = await client.post(
            "/auth/magic-link",
            json={"email": ADMIN_PAYLOAD["email"]},
            headers=_from("203.0.113.1"),
        )

    assert refused.status_code == 429
    assert sent.await_count == allowance


async def test_a_burst_of_magic_token_guesses_ends_in_429(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    allowance = get_rate_limit_config().token_max_attempts

    for _ in range(allowance):
        response = await client.post(
            "/auth/magic-link/verify",
            json={"token": "guess"},
            headers=_from("203.0.113.1"),
        )
        assert response.status_code == 401

    refused = await client.post(
        "/auth/magic-link/verify", json={"token": "guess"}, headers=_from("203.0.113.1")
    )
    assert refused.status_code == 429


async def test_a_burst_of_refresh_token_guesses_ends_in_429(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    allowance = get_rate_limit_config().token_max_attempts

    for _ in range(allowance):
        response = await client.post(
            "/auth/refresh", json={"refresh_token": "guess"}, headers=_from("203.0.113.1")
        )
        assert response.status_code == 401

    refused = await client.post(
        "/auth/refresh", json={"refresh_token": "guess"}, headers=_from("203.0.113.1")
    )
    assert refused.status_code == 429


async def test_the_refresh_allowance_is_counted_per_address(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    for _ in range(get_rate_limit_config().token_max_attempts + 1):
        await client.post(
            "/auth/refresh", json={"refresh_token": "guess"}, headers=_from("203.0.113.1")
        )

    response = await client.post(
        "/auth/refresh", json={"refresh_token": "guess"}, headers=_from("198.51.100.7")
    )

    assert response.status_code == 401
