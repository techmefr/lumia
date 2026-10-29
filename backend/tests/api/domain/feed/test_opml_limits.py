from collections.abc import AsyncIterator

import httpx
import pytest

from api.domain.feed.opml_service import MAX_OPML_ENTRIES
from api.main import app
from api.technical.net.url_guard import get_url_resolver
from config.rate_limit import get_rate_limit_config
from worker.technical.connectors.miniflux_client import get_miniflux_transport

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


def _miniflux_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET":
        return httpx.Response(200, json=[])
    return httpx.Response(201, json={"feed_id": 1})


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(
        _miniflux_handler
    )
    app.dependency_overrides[get_url_resolver] = lambda: lambda host: ["93.184.216.34"]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.pop(get_miniflux_transport, None)
    app.dependency_overrides.pop(get_url_resolver, None)


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _opml(entries: int) -> bytes:
    outlines = "".join(
        f'<outline type="rss" text="Feed {index}" xmlUrl="https://example.com/{index}.xml"/>'
        for index in range(entries)
    )
    return f'<?xml version="1.0"?><opml version="1.0"><body>{outlines}</body></opml>'.encode()


async def _import(
    client: httpx.AsyncClient, headers: dict[str, str], body: bytes
) -> httpx.Response:
    return await client.post(
        "/feeds/import-opml", headers=headers, files={"file": ("feeds.opml", body)}
    )


async def test_an_import_over_the_entry_ceiling_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await _import(client, headers, _opml(MAX_OPML_ENTRIES + 1))

    assert response.status_code == 413
    assert (await client.get("/feeds", headers=headers)).json() == []


async def test_an_import_at_the_entry_ceiling_goes_through(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await _import(client, headers, _opml(2))

    assert response.status_code == 200


async def test_imports_are_rate_limited_per_reader(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    allowance = get_rate_limit_config().opml_import_max_attempts

    statuses = [
        (await _import(client, headers, _opml(1))).status_code for _ in range(allowance + 1)
    ]

    assert statuses[:allowance] == [200] * allowance
    assert statuses[-1] == 429
