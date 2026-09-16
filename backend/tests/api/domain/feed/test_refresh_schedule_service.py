from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.models import Feed, SourceType
from api.domain.feed.refresh_schedule_service import list_feeds_due_for_refresh, mark_refreshed
from api.domain.user.models import Instance, User
from config.database import get_engine

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _add_feed(
    session: AsyncSession,
    *,
    interval: int | None,
    last_refreshed_at: datetime | None,
    source_type: SourceType = SourceType.MINIFLUX,
    external_feed_id: str = "7",
) -> Feed:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email=f"{uuid4()}@example.com", username="reader")
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=source_type,
        external_feed_id=external_feed_id,
        title="A blog",
        url=f"https://blog.test/{external_feed_id}/rss",
        refresh_interval_minutes=interval,
        last_refreshed_at=last_refreshed_at,
    )
    session.add(feed)
    await session.commit()
    return feed


async def test_a_feed_whose_interval_has_elapsed_is_due(session: AsyncSession) -> None:
    await _add_feed(session, interval=30, last_refreshed_at=NOW - timedelta(minutes=31))

    assert len(await list_feeds_due_for_refresh(session, now=NOW)) == 1


async def test_a_feed_refreshed_within_its_interval_is_left_alone(session: AsyncSession) -> None:
    await _add_feed(session, interval=30, last_refreshed_at=NOW - timedelta(minutes=29))

    assert await list_feeds_due_for_refresh(session, now=NOW) == []


async def test_a_feed_with_no_interval_is_never_nudged(session: AsyncSession) -> None:
    """Miniflux already polls it on the instance's own schedule; nudging would duplicate that."""
    await _add_feed(session, interval=None, last_refreshed_at=NOW - timedelta(days=30))

    assert await list_feeds_due_for_refresh(session, now=NOW) == []


async def test_a_freshly_set_interval_takes_effect_at_the_next_tick(session: AsyncSession) -> None:
    """Never refreshed means due now, rather than due one full interval from now."""
    await _add_feed(session, interval=1440, last_refreshed_at=None)

    assert len(await list_feeds_due_for_refresh(session, now=NOW)) == 1


async def test_a_manual_feed_is_never_nudged(session: AsyncSession) -> None:
    """A saved page has no feed behind it for Miniflux to fetch."""
    await _add_feed(session, interval=30, last_refreshed_at=None, source_type=SourceType.MANUAL)

    assert await list_feeds_due_for_refresh(session, now=NOW) == []


async def test_marking_refreshed_pushes_the_next_run_a_full_interval_away(
    session: AsyncSession,
) -> None:
    feed = await _add_feed(session, interval=30, last_refreshed_at=None)

    await mark_refreshed(session, [feed])

    assert await list_feeds_due_for_refresh(session, now=datetime.now(UTC)) == []
