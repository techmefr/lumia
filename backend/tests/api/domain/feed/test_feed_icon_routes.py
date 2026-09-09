from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import User
from api.main import app
from config.database import get_engine
from worker.technical.connectors.miniflux_client import get_miniflux_transport

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"
# A 1x1 transparent PNG.
PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_feed(source_type: SourceType = SourceType.MINIFLUX) -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=source_type,
            external_feed_id="7",
            title="Feed",
            url="https://example.com/feed",
        )
        session.add(feed)
        await session.commit()
        return str(feed.id)


def _use_miniflux(handler: object) -> None:
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(handler)  # type: ignore[arg-type]


async def test_feed_icon_is_decoded_and_served(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/feeds/7/icon"
        return httpx.Response(
            200, json={"id": 1, "mime_type": "image/png", "data": f"image/png;base64,{PNG_BASE64}"}
        )

    _use_miniflux(handler)

    response = await client.get(f"/feeds/{feed_id}/icon", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


async def test_feed_without_an_icon_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed()
    _use_miniflux(lambda request: httpx.Response(404, json={"error_message": "not found"}))

    response = await client.get(f"/feeds/{feed_id}/icon", headers=headers)
    assert response.status_code == 404


async def test_malformed_icon_payload_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed()
    _use_miniflux(lambda request: httpx.Response(200, json={"id": 1, "data": "not-base64-at-all"}))

    response = await client.get(f"/feeds/{feed_id}/icon", headers=headers)
    assert response.status_code == 404


async def test_manual_feed_has_no_icon(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed(SourceType.MANUAL)

    response = await client.get(f"/feeds/{feed_id}/icon", headers=headers)
    assert response.status_code == 404


async def test_unknown_feed_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.get(f"/feeds/{UNKNOWN_ID}/icon", headers=headers)
    assert response.status_code == 404
