from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.models import Feed, SourceType


async def list_feeds_due_for_refresh(session: AsyncSession, *, now: datetime) -> Sequence[Feed]:
    """Feeds whose own interval has elapsed since the last refresh was asked for.

    A feed with no interval is left alone entirely: Miniflux already polls it on the instance's
    schedule, and nudging it here would only duplicate that. A feed that carries an interval but
    was never refreshed is due immediately, so a freshly set interval takes effect at the next
    tick rather than one full interval later.

    The elapsed check is done in Python rather than SQL: only feeds carrying an interval are
    fetched at all, which is a small set, and an interval-typed comparison against a column has no
    portable spelling across the dialects the test suite and production run on.
    """
    candidates: Sequence[Feed] = (
        await session.scalars(
            select(Feed).where(
                Feed.source_type == SourceType.MINIFLUX,
                Feed.refresh_interval_minutes.is_not(None),
            )
        )
    ).all()
    return [feed for feed in candidates if _is_due(feed, now=now)]


def _is_due(feed: Feed, *, now: datetime) -> bool:
    if feed.refresh_interval_minutes is None:
        return False
    if feed.last_refreshed_at is None:
        return True
    return now - feed.last_refreshed_at >= timedelta(minutes=feed.refresh_interval_minutes)


async def mark_refreshed(session: AsyncSession, feeds: Sequence[Feed]) -> None:
    now = datetime.now(UTC)
    for feed in feeds:
        feed.last_refreshed_at = now
    await session.commit()
