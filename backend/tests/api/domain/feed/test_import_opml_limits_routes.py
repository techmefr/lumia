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

BILLION_LAUGHS = b"""<?xml version="1.0"?>
<!DOCTYPE opml [
  <!ENTITY a "dos">
  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
  <!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">
  <!ENTITY d "&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;">
]>
<opml version="1.0">
  <body><outline type="rss" title="&d;" xmlUrl="https://example.com/feed"/></body>
</opml>
"""


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
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(
        _miniflux_handler
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_an_upload_over_the_cap_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    oversized = b"<opml><body>" + b"<!-- padding -->" * 200_000 + b"</body></opml>"

    response = await client.post(
        "/feeds/import-opml",
        files={"file": ("big.opml", oversized, "text/xml")},
        headers=headers,
    )

    assert response.status_code == 413


async def test_an_entity_expansion_document_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/feeds/import-opml",
        files={"file": ("bomb.opml", BILLION_LAUGHS, "text/xml")},
        headers=headers,
    )

    assert response.status_code == 400
