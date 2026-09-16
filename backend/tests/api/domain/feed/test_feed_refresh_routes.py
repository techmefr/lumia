from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import User
from api.main import app
from config.database import get_engine
from config.rate_limit import get_rate_limit_config
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


async def _seed_feed(
    source_type: SourceType = SourceType.MINIFLUX, *, external_feed_id: str = "7"
) -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=source_type,
            external_feed_id=external_feed_id,
            title="A blog",
            url=f"https://blog.test/{external_feed_id}/rss?token=secret",
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
    assert body["last_refreshed_at"] is not None
    # PUT, not POST: Miniflux registers this route for PUT alone, so a POST is a 405 and the
    # feed is never actually fetched.
    assert "PUT /v1/feeds/7/refresh" in calls
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


async def test_a_reader_hammering_one_feed_is_capped(client: httpx.AsyncClient) -> None:
    """A manual refresh reaches a publisher's server, so a page stuck retrying must hit a wall."""
    headers = await _headers(client)
    feed_id = await _seed_feed()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/refresh"):
            return httpx.Response(204)
        return httpx.Response(
            200,
            json={
                "id": 7,
                "title": "A blog",
                "parsing_error_count": 0,
                "parsing_error_message": "",
            },
        )

    _use_miniflux(handler)

    allowance = get_rate_limit_config().feed_refresh_max_attempts
    for _ in range(allowance):
        assert (await client.post(f"/feeds/{feed_id}/refresh", headers=headers)).status_code == 200

    capped = await client.post(f"/feeds/{feed_id}/refresh", headers=headers)

    assert capped.status_code == 429
    assert capped.headers["Retry-After"]


async def test_spending_one_feeds_allowance_leaves_another_feed_refreshable(
    client: httpx.AsyncClient,
) -> None:
    """Chasing one broken feed must not cost the reader the right to refresh a different one."""
    headers = await _headers(client)
    chased = await _seed_feed()
    other = await _seed_feed(external_feed_id="8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/refresh"):
            return httpx.Response(204)
        return httpx.Response(
            200,
            json={
                "id": 7,
                "title": "A blog",
                "parsing_error_count": 0,
                "parsing_error_message": "",
            },
        )

    _use_miniflux(handler)

    for _ in range(get_rate_limit_config().feed_refresh_max_attempts + 1):
        await client.post(f"/feeds/{chased}/refresh", headers=headers)

    assert (await client.post(f"/feeds/{other}/refresh", headers=headers)).status_code == 200


async def test_refreshing_everything_asks_miniflux_once_for_the_whole_account(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seed_feed()
    await _seed_feed(external_feed_id="8")
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(204)

    _use_miniflux(handler)

    response = await client.post("/feeds/refresh", headers=headers)

    assert response.status_code == 200
    # One account-wide call, not one per feed: Miniflux paces the batch itself.
    assert calls == ["PUT /v1/feeds/refresh"]
    assert response.json()["feeds_requested"] == 2


async def test_refreshing_everything_reports_feeds_asked_for_never_articles_fetched(
    client: httpx.AsyncClient,
) -> None:
    """Articles arrive later over the webhook, so the response must not imply any landed."""
    headers = await _headers(client)
    await _seed_feed()
    _use_miniflux(lambda request: httpx.Response(204))

    body = (await client.post("/feeds/refresh", headers=headers)).json()

    assert set(body) == {"feeds_requested", "requested_at"}
    assert "articles" not in body


async def test_refreshing_everything_is_capped_far_tighter_than_a_single_feed(
    client: httpx.AsyncClient,
) -> None:
    """One click pulls every feed on the instance, other readers' included."""
    headers = await _headers(client)
    await _seed_feed()
    _use_miniflux(lambda request: httpx.Response(204))

    config = get_rate_limit_config()
    assert config.feed_refresh_all_max_attempts < config.feed_refresh_max_attempts

    for _ in range(config.feed_refresh_all_max_attempts):
        assert (await client.post("/feeds/refresh", headers=headers)).status_code == 200

    assert (await client.post("/feeds/refresh", headers=headers)).status_code == 429


async def test_refresh_is_not_mistaken_for_a_feed_id(client: httpx.AsyncClient) -> None:
    """/feeds/refresh must reach the account route, not be parsed as a feed id and 422."""
    headers = await _headers(client)
    _use_miniflux(lambda request: httpx.Response(204))

    response = await client.post("/feeds/refresh", headers=headers)

    assert response.status_code == 200


async def test_an_unreachable_miniflux_fails_the_whole_account_refresh_cleanly(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seed_feed()
    _use_miniflux(lambda request: httpx.Response(500, text="internal error"))

    response = await client.post("/feeds/refresh", headers=headers)

    assert response.status_code == 502
