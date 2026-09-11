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
            title="A blog",
            url="https://blog.test/rss?token=secret",
        )
        session.add(feed)
        await session.commit()
        return str(feed.id)


def _use_miniflux(handler: object) -> None:
    app.dependency_overrides[get_miniflux_transport] = lambda: httpx.MockTransport(handler)  # type: ignore[arg-type]


async def test_refreshing_a_feed_asks_miniflux_and_stores_its_new_status(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path == "/v1/feeds/7/refresh":
            return httpx.Response(204)
        if request.url.path == "/v1/feeds/7":
            return httpx.Response(
                200,
                json={
                    "id": 7,
                    "title": "A blog",
                    "parsing_error_count": 5,
                    "parsing_error_message": "404 Not Found",
                },
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    _use_miniflux(handler)

    response = await client.post(f"/feeds/{feed_id}/refresh", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["error_count"] == 5
    assert body["error_reason"] == "not_found"
    assert body["error_since"] is not None
    assert "POST /v1/feeds/7/refresh" in calls
    assert "GET /v1/feeds/7" in calls


async def test_the_reader_never_sees_the_providers_raw_error_text(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/feeds/7/refresh":
            return httpx.Response(204)
        return httpx.Response(
            200,
            json={
                "id": 7,
                "title": "A blog",
                "parsing_error_count": 1,
                "parsing_error_message": "dial tcp 10.0.0.1:443: i/o timeout on attacker-supplied-url",
            },
        )

    _use_miniflux(handler)

    response = await client.post(f"/feeds/{feed_id}/refresh", headers=headers)

    assert response.status_code == 200
    assert "attacker-supplied-url" not in response.text
    assert "10.0.0.1" not in response.text
    assert response.json()["error_reason"] == "unreachable"


async def test_refreshing_an_unknown_feed_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.post(f"/feeds/{UNKNOWN_ID}/refresh", headers=headers)
    assert response.status_code == 404


async def test_refreshing_a_manual_feed_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed(SourceType.MANUAL)

    response = await client.post(f"/feeds/{feed_id}/refresh", headers=headers)

    assert response.status_code == 404


async def test_a_miniflux_failure_surfaces_as_a_bad_gateway_not_a_crash(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    feed_id = await _seed_feed()
    _use_miniflux(lambda request: httpx.Response(500, text="internal error"))

    response = await client.post(f"/feeds/{feed_id}/refresh", headers=headers)

    assert response.status_code == 502
