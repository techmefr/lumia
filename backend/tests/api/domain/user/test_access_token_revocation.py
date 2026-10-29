from collections.abc import AsyncIterator

import httpx
import pyotp
import pytest

from api.main import app

PASSWORD = "correct-horse-battery-staple"
ADMIN_PAYLOAD = {"email": "admin@example.com", "username": "admin", "password": PASSWORD}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _sign_up(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    tokens: dict[str, str] = response.json()
    return tokens


def _bearer(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_a_fresh_access_token_is_accepted(client: httpx.AsyncClient) -> None:
    tokens = await _sign_up(client)
    assert (await client.get("/me", headers=_bearer(tokens))).status_code == 200


async def test_logout_revokes_the_access_token_immediately(client: httpx.AsyncClient) -> None:
    tokens = await _sign_up(client)
    await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert (await client.get("/me", headers=_bearer(tokens))).status_code == 401


async def test_logout_all_revokes_the_access_token_immediately(client: httpx.AsyncClient) -> None:
    tokens = await _sign_up(client)
    await client.post("/auth/logout-all", headers=_bearer(tokens))
    assert (await client.get("/me", headers=_bearer(tokens))).status_code == 401


async def test_changing_the_password_revokes_old_tokens_and_the_new_pair_works(
    client: httpx.AsyncClient,
) -> None:
    tokens = await _sign_up(client)
    response = await client.post(
        "/me/password",
        headers=_bearer(tokens),
        json={"current_password": PASSWORD, "new_password": "another-long-passphrase-1"},
    )
    assert response.status_code == 200
    assert (await client.get("/me", headers=_bearer(tokens))).status_code == 401
    assert (await client.get("/me", headers=_bearer(response.json()))).status_code == 200


async def test_refreshing_keeps_the_current_session_version(client: httpx.AsyncClient) -> None:
    tokens = await _sign_up(client)
    refreshed = (
        await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).json()
    assert (await client.get("/me", headers=_bearer(refreshed))).status_code == 200


async def test_disabling_totp_revokes_the_access_token(client: httpx.AsyncClient) -> None:
    tokens = await _sign_up(client)
    headers = _bearer(tokens)
    secret = (await client.post("/me/totp/enrolment", headers=headers)).json()["secret"]
    await client.post("/me/totp", headers=headers, json={"code": pyotp.TOTP(secret).now()})
    response = await client.request(
        "DELETE", "/me/totp", headers=headers, json={"password": PASSWORD}
    )
    assert response.status_code == 204
    assert (await client.get("/me", headers=headers)).status_code == 401
