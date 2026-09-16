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
NEW_PASSWORD = "another-horse-battery-staple"


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _onboard(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert response.status_code == 201
    tokens: dict[str, str] = response.json()
    return tokens


def _auth(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _request_reset_link(client: httpx.AsyncClient, raw_token: str) -> None:
    with (
        patch("api.domain.user.magic_link_service.send_email", new_callable=AsyncMock),
        patch(
            "api.domain.user.magic_link_service.generate_opaque_token",
            return_value=raw_token,
        ),
    ):
        response = await client.post(
            "/auth/magic-link",
            json={"email": ADMIN_PAYLOAD["email"], "purpose": "password_reset"},
        )
    assert response.status_code == 202


async def test_changing_the_password_lets_the_new_one_sign_in(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)

    response = await client.post(
        "/me/password",
        headers=_auth(tokens),
        json={"current_password": ADMIN_PAYLOAD["password"], "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 200

    signed_in = await client.post(
        "/auth/login", json={"email": ADMIN_PAYLOAD["email"], "password": NEW_PASSWORD}
    )
    assert signed_in.status_code == 200


async def test_the_former_password_no_longer_signs_in(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)
    await client.post(
        "/me/password",
        headers=_auth(tokens),
        json={"current_password": ADMIN_PAYLOAD["password"], "new_password": NEW_PASSWORD},
    )

    refused = await client.post(
        "/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
    )
    assert refused.status_code == 401


async def test_a_wrong_current_password_changes_nothing(client: httpx.AsyncClient) -> None:
    tokens = await _onboard(client)

    response = await client.post(
        "/me/password",
        headers=_auth(tokens),
        json={"current_password": "not-the-one", "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 401

    unchanged = await client.post(
        "/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
    )
    assert unchanged.status_code == 200


async def test_omitting_the_current_password_is_not_a_way_past_it(
    client: httpx.AsyncClient,
) -> None:
    """A missing field is not an absent password: leaving it out would be the shortest bypass."""
    tokens = await _onboard(client)

    response = await client.post(
        "/me/password", headers=_auth(tokens), json={"new_password": NEW_PASSWORD}
    )
    assert response.status_code == 401


async def test_changing_a_password_needs_a_signed_in_reader(client: httpx.AsyncClient) -> None:
    await _onboard(client)

    response = await client.post(
        "/me/password",
        json={"current_password": ADMIN_PAYLOAD["password"], "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 401


async def test_a_new_password_shorter_than_the_floor_is_refused(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)

    response = await client.post(
        "/me/password",
        headers=_auth(tokens),
        json={"current_password": ADMIN_PAYLOAD["password"], "new_password": "short1"},
    )
    assert response.status_code == 422


async def test_the_change_ends_the_sessions_opened_before_it(client: httpx.AsyncClient) -> None:
    """The refresh token issued under the old password would otherwise outlive it by a month."""
    tokens = await _onboard(client)

    await client.post(
        "/me/password",
        headers=_auth(tokens),
        json={"current_password": ADMIN_PAYLOAD["password"], "new_password": NEW_PASSWORD},
    )

    refused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refused.status_code == 401


async def test_the_change_hands_back_a_usable_pair(client: httpx.AsyncClient) -> None:
    """Revoking every session would otherwise sign the reader out of the device they just used."""
    tokens = await _onboard(client)

    response = await client.post(
        "/me/password",
        headers=_auth(tokens),
        json={"current_password": ADMIN_PAYLOAD["password"], "new_password": NEW_PASSWORD},
    )

    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": response.json()["refresh_token"]}
    )
    assert refreshed.status_code == 200


async def test_a_burst_of_current_password_guesses_ends_in_429(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _onboard(client)
    allowance = get_rate_limit_config().login_max_attempts

    for _ in range(allowance):
        response = await client.post(
            "/me/password",
            headers=_auth(tokens),
            json={"current_password": "not-the-one", "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 401

    refused = await client.post(
        "/me/password",
        headers=_auth(tokens),
        json={"current_password": "not-the-one", "new_password": NEW_PASSWORD},
    )
    assert refused.status_code == 429


async def test_a_reset_link_sets_a_password_without_the_former_one(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _request_reset_link(client, "reset-token")

    response = await client.post(
        "/auth/password-reset", json={"token": "reset-token", "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 200

    signed_in = await client.post(
        "/auth/login", json={"email": ADMIN_PAYLOAD["email"], "password": NEW_PASSWORD}
    )
    assert signed_in.status_code == 200


async def test_the_reset_link_signs_the_reader_in_straight_away(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _request_reset_link(client, "reset-token")

    response = await client.post(
        "/auth/password-reset", json={"token": "reset-token", "new_password": NEW_PASSWORD}
    )

    me = await client.get("/me", headers=_auth(response.json()))
    assert me.status_code == 200
    assert me.json()["email"] == ADMIN_PAYLOAD["email"]


async def test_a_reset_token_cannot_be_replayed(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    await _request_reset_link(client, "reset-token")
    await client.post(
        "/auth/password-reset", json={"token": "reset-token", "new_password": NEW_PASSWORD}
    )

    replayed = await client.post(
        "/auth/password-reset", json={"token": "reset-token", "new_password": "a-third-password"}
    )
    assert replayed.status_code == 401


async def test_an_unknown_reset_token_is_refused(client: httpx.AsyncClient) -> None:
    await _onboard(client)

    response = await client.post(
        "/auth/password-reset", json={"token": "never-issued", "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 401


async def test_a_reset_refuses_a_password_shorter_than_the_floor(
    client: httpx.AsyncClient,
) -> None:
    await _onboard(client)
    await _request_reset_link(client, "reset-token")

    response = await client.post(
        "/auth/password-reset", json={"token": "reset-token", "new_password": "short1"}
    )
    assert response.status_code == 422


async def test_the_reset_ends_the_sessions_opened_before_it(client: httpx.AsyncClient) -> None:
    """A forgotten password is the case where somebody else may be holding a live session."""
    tokens = await _onboard(client)
    await _request_reset_link(client, "reset-token")

    await client.post(
        "/auth/password-reset", json={"token": "reset-token", "new_password": NEW_PASSWORD}
    )

    refused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refused.status_code == 401


async def test_a_burst_of_reset_token_guesses_ends_in_429(client: httpx.AsyncClient) -> None:
    await _onboard(client)
    allowance = get_rate_limit_config().token_max_attempts

    for _ in range(allowance):
        response = await client.post(
            "/auth/password-reset",
            json={"token": "guess", "new_password": NEW_PASSWORD},
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert response.status_code == 401

    refused = await client.post(
        "/auth/password-reset",
        json={"token": "guess", "new_password": NEW_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.1"},
    )
    assert refused.status_code == 429
