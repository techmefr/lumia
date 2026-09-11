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

FEEDLY_OPML = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <body>
    <outline type="rss" text="Hacker News" title="Hacker News"
             xmlUrl="https://hnrss.org/frontpage" htmlUrl="https://news.ycombinator.com"/>
  </body>
</opml>
"""


def _resolve_to_the_public_internet(host: str) -> list[str]:
    return ["93.184.216.34"]


def _miniflux_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/v1/feeds":
        return httpx.Response(200, json=[])
    if request.method == "GET" and request.url.path == "/v1/categories":
        return httpx.Response(200, json=[])
    if request.method == "POST" and request.url.path == "/v1/feeds":
        return httpx.Response(201, json={"feed_id": 7})
    raise AssertionError(f"unexpected request {request.method} {request.url}")


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(
        _miniflux_handler
    )
    app.dependency_overrides[get_url_resolver] = lambda: _resolve_to_the_public_internet
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_miniflux_transport, None)
    app.dependency_overrides.pop(get_url_resolver, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_import_opml_creates_feeds_from_the_uploaded_file(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/import-opml",
        headers=headers,
        files={"file": ("feeds.opml", FEEDLY_OPML, "text/x-opml")},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["url"] == "https://hnrss.org/frontpage"
    assert body[0]["external_feed_id"] == "7"


async def test_import_opml_rejects_a_malformed_file(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/import-opml",
        headers=headers,
        files={"file": ("feeds.opml", b"not xml", "text/x-opml")},
    )

    assert response.status_code == 400


async def test_import_opml_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/feeds/import-opml",
        files={"file": ("feeds.opml", FEEDLY_OPML, "text/x-opml")},
    )
    assert response.status_code == 401
