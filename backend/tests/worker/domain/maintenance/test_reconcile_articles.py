from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import Instance, User
from config.database import get_engine
from worker.domain.maintenance.reconcile_articles import reconcile_recent_articles


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


def _entry(entry_id: str, feed_id: str = "11") -> dict[str, Any]:
    return {
        "id": entry_id,
        "title": f"Entry {entry_id}",
        "url": f"https://blog.test/{entry_id}",
        "content": "<p>Body</p>",
        "published_at": datetime.now(UTC).isoformat(),
        "author": "A. Writer",
        "feed": {"id": feed_id, "category": {"title": "Tech"}},
    }


def _miniflux_serving(*entries: dict[str, Any]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/entries"
        assert "published_after" in request.url.params
        return httpx.Response(200, json={"total": len(entries), "entries": list(entries)})

    return httpx.MockTransport(handler)


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


async def _store_article(session: AsyncSession, feed: Feed, external_entry_id: str) -> None:
    session.add(
        Article(
            feed_id=feed.id,
            external_entry_id=external_entry_id,
            title="Already here",
            url="https://blog.test/already",
            content="<p>Body</p>",
            published_at=datetime.now(UTC),
        )
    )
    await session.commit()


def _queued_entry_ids(pool: AsyncMock) -> list[str]:
    return [call.args[1].external_entry_id for call in pool.enqueue_job.await_args_list]


async def test_an_entry_that_never_arrived_is_queued(session: AsyncSession) -> None:
    """This is the lost webhook: Miniflux has the entry, the database does not."""
    await _subscribe(session, "11")
    pool = AsyncMock()

    queued = await reconcile_recent_articles(
        {"redis": pool}, transport=_miniflux_serving(_entry("101"))
    )

    assert queued == 1
    assert _queued_entry_ids(pool) == ["101"]


async def test_an_entry_already_stored_is_left_alone(session: AsyncSession) -> None:
    feed = await _subscribe(session, "11")
    await _store_article(session, feed, "101")
    pool = AsyncMock()

    queued = await reconcile_recent_articles(
        {"redis": pool}, transport=_miniflux_serving(_entry("101"))
    )

    assert queued == 0
    pool.enqueue_job.assert_not_awaited()


async def test_only_the_missing_entries_of_a_mixed_batch_are_queued(
    session: AsyncSession,
) -> None:
    feed = await _subscribe(session, "11")
    await _store_article(session, feed, "101")
    pool = AsyncMock()

    await reconcile_recent_articles(
        {"redis": pool},
        transport=_miniflux_serving(_entry("101"), _entry("102"), _entry("103")),
    )

    assert _queued_entry_ids(pool) == ["102", "103"]


async def test_an_entry_of_a_feed_nobody_subscribes_to_is_skipped(
    session: AsyncSession,
) -> None:
    """Enrichment resolves the feed rows itself and does nothing without them: queueing those
    entries would be an hourly no-op forever."""
    await _subscribe(session, "11")
    pool = AsyncMock()

    queued = await reconcile_recent_articles(
        {"redis": pool}, transport=_miniflux_serving(_entry("999", feed_id="42"))
    )

    assert queued == 0
    pool.enqueue_job.assert_not_awaited()


async def test_an_empty_window_queues_nothing(session: AsyncSession) -> None:
    await _subscribe(session, "11")
    pool = AsyncMock()

    assert await reconcile_recent_articles({"redis": pool}, transport=_miniflux_serving()) == 0
    pool.enqueue_job.assert_not_awaited()


async def test_the_queued_entry_carries_what_enrichment_needs(session: AsyncSession) -> None:
    await _subscribe(session, "11")
    pool = AsyncMock()

    await reconcile_recent_articles({"redis": pool}, transport=_miniflux_serving(_entry("101")))

    assert pool.enqueue_job.await_args is not None
    assert pool.enqueue_job.await_args.args[0] == "enrich_article"
    article = pool.enqueue_job.await_args.args[1]
    assert article.feed_external_id == "11"
    assert article.url == "https://blog.test/101"
    assert article.author_name == "A. Writer"
    assert article.category_name == "Tech"


async def test_the_window_asked_of_miniflux_is_bounded(session: AsyncSession) -> None:
    """Without a bound the pass would ask Miniflux for its whole history every hour."""
    await _subscribe(session, "11")
    asked: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        asked.update(request.url.params)
        return httpx.Response(200, json={"total": 0, "entries": []})

    await reconcile_recent_articles({"redis": AsyncMock()}, transport=httpx.MockTransport(handler))

    published_after = datetime.fromtimestamp(int(asked["published_after"]), tz=UTC)
    assert timedelta(hours=23) < datetime.now(UTC) - published_after < timedelta(hours=25)
    assert int(asked["limit"]) > 0
