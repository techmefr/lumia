from collections.abc import AsyncIterator

import httpx
import pytest

from api.main import app
from worker.technical.connectors.miniflux_client import get_miniflux_transport

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


def _miniflux_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/v1/categories":
        return httpx.Response(200, json=[])
    if request.method == "POST" and request.url.path == "/v1/feeds":
        return httpx.Response(201, json={"feed_id": 7})
    if request.method == "GET" and request.url.path == "/v1/feeds/7":
        return httpx.Response(200, json={"id": 7, "title": "Hacker News"})
    raise AssertionError(f"unexpected request {request.method} {request.url}")


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(
        _miniflux_handler
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_miniflux_transport, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_add_feed_by_url_creates_the_feed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/add-by-url",
        headers=headers,
        json={"url": "https://hnrss.org/frontpage"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://hnrss.org/frontpage"
    assert body["title"] == "Hacker News"
    assert body["folder_id"] is None


async def test_add_feed_by_url_returns_404_for_a_foreign_folder(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/add-by-url",
        headers=headers,
        json={
            "url": "https://hnrss.org/frontpage",
            "folder_id": "00000000-0000-0000-0000-000000000000",
        },
    )

    assert response.status_code == 404


async def test_add_feed_by_url_returns_400_when_the_feed_is_unreachable(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/feeds":
            return httpx.Response(502, text="upstream feed unreachable")
        return _miniflux_handler(request)

    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(handler)

    response = await client.post(
        "/feeds/add-by-url",
        headers=headers,
        json={"url": "https://example.com/broken.xml"},
    )

    assert response.status_code == 400


async def test_add_feed_by_url_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/feeds/add-by-url",
        json={"url": "https://hnrss.org/frontpage"},
    )
    assert response.status_code == 401
