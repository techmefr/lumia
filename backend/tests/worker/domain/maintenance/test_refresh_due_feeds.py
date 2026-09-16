from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import Instance, User
from config.database import get_engine
from worker.domain.maintenance.refresh_due_feeds import refresh_due_feeds


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _add_feed(
    session: AsyncSession, *, interval: int | None, external_feed_id: str, stale_minutes: int = 120
) -> Feed:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="reader")
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_feed_id,
        title="A blog",
        url=f"https://blog.test/{external_feed_id}/rss",
        refresh_interval_minutes=interval,
        last_refreshed_at=datetime.now(UTC) - timedelta(minutes=stale_minutes),
    )
    session.add(feed)
    await session.commit()
    return feed


def _recording_transport(calls: list[str]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        return httpx.Response(204)

    return httpx.MockTransport(handler)


async def test_a_due_feed_is_nudged_on_miniflux(session: AsyncSession) -> None:
    await _add_feed(session, interval=30, external_feed_id="7")
    calls: list[str] = []

    nudged = await refresh_due_feeds({}, transport=_recording_transport(calls))

    assert nudged == 1
    assert calls == ["PUT /v1/feeds/7/refresh"]


async def test_a_feed_that_is_not_due_is_not_touched(session: AsyncSession) -> None:
    await _add_feed(session, interval=180, external_feed_id="7", stale_minutes=10)
    calls: list[str] = []

    nudged = await refresh_due_feeds({}, transport=_recording_transport(calls))

    assert nudged == 0
    assert calls == []


async def test_one_miniflux_feed_shared_by_two_readers_is_refreshed_once(
    session: AsyncSession,
) -> None:
    """Refreshing the same feed once per subscriber would multiply the load on the publisher."""
    await _add_feed(session, interval=30, external_feed_id="7")
    await _add_feed(session, interval=30, external_feed_id="7")
    calls: list[str] = []

    nudged = await refresh_due_feeds({}, transport=_recording_transport(calls))

    assert nudged == 1
    assert calls == ["PUT /v1/feeds/7/refresh"]


async def test_a_feed_miniflux_rejects_does_not_sink_the_run(session: AsyncSession) -> None:
    await _add_feed(session, interval=30, external_feed_id="7")
    await _add_feed(session, interval=30, external_feed_id="8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/feeds/7/refresh":
            return httpx.Response(500, text="boom")
        return httpx.Response(204)

    nudged = await refresh_due_feeds({}, transport=httpx.MockTransport(handler))

    assert nudged == 2


async def test_a_broken_feed_is_not_retried_on_every_tick(session: AsyncSession) -> None:
    """Marking it attempted anyway is what keeps a permanently dead feed off every run."""
    await _add_feed(session, interval=30, external_feed_id="7")
    failing = httpx.MockTransport(lambda request: httpx.Response(500, text="boom"))

    assert await refresh_due_feeds({}, transport=failing) == 1
    calls: list[str] = []
    assert await refresh_due_feeds({}, transport=_recording_transport(calls)) == 0
    assert calls == []
