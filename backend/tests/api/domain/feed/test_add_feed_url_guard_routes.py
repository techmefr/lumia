from collections.abc import AsyncIterator

import httpx
import pytest

from api.main import app
from api.technical.net.url_guard import get_url_resolver
from worker.technical.connectors.miniflux_client import get_miniflux_transport

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}

LOOPBACK_OPML = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <body>
    <outline type="rss" text="Interne" title="Interne" xmlUrl="http://internal.test/feed"/>
    <outline type="rss" text="Public" title="Public" xmlUrl="https://example.com/feed"/>
  </body>
</opml>
"""


def _resolve(host: str) -> list[str]:
    return ["93.184.216.34"] if host == "example.com" else ["127.0.0.1"]


@pytest.fixture
async def miniflux_calls() -> list[str]:
    return []


@pytest.fixture
async def client(db_schema: None, miniflux_calls: list[str]) -> AsyncIterator[httpx.AsyncClient]:
    def handler(request: httpx.Request) -> httpx.Response:
        miniflux_calls.append(str(request.url))
        if request.method == "GET" and request.url.path == "/v1/feeds":
            return httpx.Response(200, json=[])
        if request.method == "GET" and request.url.path == "/v1/categories":
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path == "/v1/feeds":
            return httpx.Response(201, json={"feed_id": 7})
        return httpx.Response(200, json={"id": 7, "title": "Public"})

    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(handler)
    app.dependency_overrides[get_url_resolver] = lambda: _resolve
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_add_feed_by_url_refuses_a_url_off_the_public_internet(
    client: httpx.AsyncClient, miniflux_calls: list[str]
) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/add-by-url", json={"url": "http://internal.test/feed"}, headers=headers
    )

    assert response.status_code == 400
    assert miniflux_calls == []


async def test_add_feed_by_url_refuses_a_non_http_scheme(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/add-by-url", json={"url": "file:///etc/passwd"}, headers=headers
    )

    assert response.status_code == 400


async def test_importing_opml_skips_the_blocked_entries_and_keeps_the_rest(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/import-opml",
        files={"file": ("feedly.opml", LOOPBACK_OPML, "text/xml")},
        headers=headers,
    )

    assert response.status_code == 200
    assert [feed["url"] for feed in response.json()] == ["https://example.com/feed"]
