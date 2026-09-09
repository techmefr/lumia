from collections.abc import AsyncIterator

import httpx
import pytest

from api.main import app

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


async def _onboarded_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


async def test_get_me_returns_the_current_user_preferences(client: httpx.AsyncClient) -> None:
    headers = await _onboarded_headers(client)

    response = await client.get("/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == ADMIN_PAYLOAD["email"]
    assert body["role"] == "admin"
    assert body["ai_api_key_set"] is False


async def test_get_me_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/me")
    assert response.status_code == 401


async def test_patch_me_updates_preferences_and_they_are_reread(
    client: httpx.AsyncClient,
) -> None:
    headers = await _onboarded_headers(client)

    patch_response = await client.patch(
        "/me",
        headers=headers,
        json={"theme": "dark", "font_base_size": 20, "ai_provider": "mistral"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["theme"] == "dark"
    assert patch_response.json()["font_base_size"] == 20

    get_response = await client.get("/me", headers=headers)
    body = get_response.json()
    assert body["theme"] == "dark"
    assert body["font_base_size"] == 20
    assert body["ai_provider"] == "mistral"


async def test_patch_me_sets_and_clears_the_ai_api_key(client: httpx.AsyncClient) -> None:
    headers = await _onboarded_headers(client)

    set_response = await client.patch("/me", headers=headers, json={"ai_api_key": "sk-secret"})
    assert set_response.json()["ai_api_key_set"] is True

    clear_response = await client.patch("/me", headers=headers, json={"ai_api_key": None})
    assert clear_response.json()["ai_api_key_set"] is False


async def test_patch_me_treats_an_empty_ai_api_key_as_a_removal(
    client: httpx.AsyncClient,
) -> None:
    headers = await _onboarded_headers(client)
    await client.patch("/me", headers=headers, json={"ai_api_key": "sk-secret"})

    response = await client.patch("/me", headers=headers, json={"ai_api_key": ""})
    assert response.json()["ai_api_key_set"] is False


async def test_patch_me_sets_and_clears_the_translation_api_key(
    client: httpx.AsyncClient,
) -> None:
    headers = await _onboarded_headers(client)

    set_response = await client.patch(
        "/me",
        headers=headers,
        json={"translation_provider": "deepl", "translation_api_key": "deepl-secret"},
    )
    assert set_response.status_code == 200
    assert set_response.json()["translation_provider"] == "deepl"
    assert set_response.json()["translation_api_key_set"] is True

    clear_response = await client.patch("/me", headers=headers, json={"translation_api_key": None})
    assert clear_response.json()["translation_api_key_set"] is False


async def test_me_never_returns_the_stored_keys(client: httpx.AsyncClient) -> None:
    headers = await _onboarded_headers(client)
    await client.patch(
        "/me",
        headers=headers,
        json={"ai_api_key": "sk-secret", "translation_api_key": "deepl-secret"},
    )

    body = await client.get("/me", headers=headers)
    assert "sk-secret" not in body.text
    assert "deepl-secret" not in body.text
    assert "ai_api_key" not in body.json()
    assert "translation_api_key" not in body.json()


async def test_patch_me_stores_the_ai_model_and_endpoint(client: httpx.AsyncClient) -> None:
    headers = await _onboarded_headers(client)

    response = await client.patch(
        "/me",
        headers=headers,
        json={
            "ai_provider": "custom",
            "ai_endpoint_url": "http://voxtral.local/v1",
            "ai_model": "voxtral-small",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ai_provider"] == "custom"
    assert body["ai_endpoint_url"] == "http://voxtral.local/v1"
    assert body["ai_model"] == "voxtral-small"


async def test_patch_me_updates_the_preferred_language(client: httpx.AsyncClient) -> None:
    headers = await _onboarded_headers(client)

    response = await client.patch("/me", headers=headers, json={"preferred_language": "en"})
    assert response.status_code == 200
    assert response.json()["preferred_language"] == "en"

    reread = await client.get("/me", headers=headers)
    assert reread.json()["preferred_language"] == "en"
