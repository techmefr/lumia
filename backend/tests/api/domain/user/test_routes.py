from collections.abc import AsyncIterator

import httpx
import pytest

from api.main import app


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


async def test_onboard_admin_creates_the_instance_and_returns_tokens(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_onboard_admin_twice_is_rejected(client: httpx.AsyncClient) -> None:
    first = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    assert first.status_code == 201

    second = await client.post(
        "/onboarding/admin",
        json={**ADMIN_PAYLOAD, "email": "second-admin@example.com"},
    )
    assert second.status_code == 409


async def test_onboard_admin_rejects_a_password_shorter_than_eight_characters(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/onboarding/admin", json={**ADMIN_PAYLOAD, "password": "short1"})
    assert response.status_code == 422


async def test_login_with_valid_credentials_returns_tokens(client: httpx.AsyncClient) -> None:
    await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)

    response = await client.post(
        "/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_login_with_invalid_password_returns_401(client: httpx.AsyncClient) -> None:
    await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)

    response = await client.post(
        "/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_login_with_unknown_email_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/auth/login", json={"email": "unknown@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


async def test_refresh_with_a_valid_refresh_token_returns_a_new_access_token(
    client: httpx.AsyncClient,
) -> None:
    onboarding = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    refresh_token = onboarding.json()["refresh_token"]

    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_refresh_with_an_unknown_refresh_token_returns_401(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/auth/refresh", json={"refresh_token": "never-issued"})
    assert response.status_code == 401


async def test_logout_revokes_the_refresh_token(client: httpx.AsyncClient) -> None:
    onboarding = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    refresh_token = onboarding.json()["refresh_token"]

    logout_response = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 204

    refresh_response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401
