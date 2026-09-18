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


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_create_then_list_returns_the_saved_search(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    created = await client.post(
        "/saved-searches", json={"name": "Rust news", "query": "rust"}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Rust news"
    assert created.json()["is_alert"] is False
    assert created.json()["unread_count"] == 0

    listed = await client.get("/saved-searches", headers=headers)
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Rust news"]


async def test_renaming_does_not_touch_the_filters(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await client.post(
        "/saved-searches", json={"name": "Rust news", "query": "rust"}, headers=headers
    )
    saved_search_id = created.json()["id"]

    updated = await client.patch(
        f"/saved-searches/{saved_search_id}", json={"name": "Rust weekly"}, headers=headers
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Rust weekly"
    assert updated.json()["query"] == "rust"


async def test_promoting_a_saved_search_to_an_alert(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await client.post(
        "/saved-searches", json={"name": "Rust news", "query": "rust"}, headers=headers
    )
    saved_search_id = created.json()["id"]

    updated = await client.patch(
        f"/saved-searches/{saved_search_id}", json={"is_alert": True}, headers=headers
    )

    assert updated.json()["is_alert"] is True


async def test_delete_removes_the_saved_search(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    created = await client.post("/saved-searches", json={"name": "Rust news"}, headers=headers)

    deleted = await client.delete(f"/saved-searches/{created.json()['id']}", headers=headers)

    assert deleted.status_code == 204
    assert (await client.get("/saved-searches", headers=headers)).json() == []


async def test_deleting_an_unknown_saved_search_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.delete(
        "/saved-searches/00000000-0000-0000-0000-000000000000", headers=headers
    )

    assert response.status_code == 404


async def test_saved_searches_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    assert (await client.get("/saved-searches")).status_code == 401
