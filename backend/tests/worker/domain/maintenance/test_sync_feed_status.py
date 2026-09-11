from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import Instance, User
from config.database import get_engine
from worker.domain.maintenance.sync_feed_status import sync_feed_error_status


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _subscribe(session: AsyncSession, external_feed_id: str) -> Feed:
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
        url="https://blog.test/rss",
    )
    session.add(feed)
    await session.commit()
    return feed


def _miniflux_listing(*feeds: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/feeds"
        return httpx.Response(200, json=list(feeds))

    return httpx.MockTransport(handler)


async def test_a_broken_feed_gets_its_error_status_mirrored(session: AsyncSession) -> None:
    feed = await _subscribe(session, "11")

    updated = await sync_feed_error_status(
        {},
        transport=_miniflux_listing(
            {
                "id": 11,
                "title": "A blog",
                "feed_url": "https://blog.test/rss",
                "parsing_error_count": 4,
                "parsing_error_message": "403 Forbidden",
            }
        ),
    )

    assert updated == 1
    await session.refresh(feed)
    assert feed.error_count == 4
    assert feed.error_reason == "forbidden"
    assert feed.error_since is not None


async def test_a_healthy_feed_is_left_with_no_error(session: AsyncSession) -> None:
    feed = await _subscribe(session, "11")

    await sync_feed_error_status(
        {},
        transport=_miniflux_listing(
            {
                "id": 11,
                "title": "A blog",
                "feed_url": "https://blog.test/rss",
                "parsing_error_count": 0,
                "parsing_error_message": "",
            }
        ),
    )

    await session.refresh(feed)
    assert feed.error_count == 0
    assert feed.error_reason is None


async def test_a_feed_nobody_subscribes_to_is_ignored(session: AsyncSession) -> None:
    await _subscribe(session, "11")

    updated = await sync_feed_error_status(
        {},
        transport=_miniflux_listing(
            {
                "id": 999,
                "title": "Someone else's feed",
                "feed_url": "https://elsewhere.test/rss",
                "parsing_error_count": 9,
                "parsing_error_message": "404 Not Found",
            }
        ),
    )

    assert updated == 0
