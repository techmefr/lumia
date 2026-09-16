import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from api.domain.feed.refresh_schedule_service import list_feeds_due_for_refresh, mark_refreshed
from worker.technical.connectors.miniflux_client import MinifluxApiError, refresh_feed
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def refresh_due_feeds(
    ctx: dict[Any, Any],
    *_args: Any,
    transport: httpx.AsyncBaseTransport | None = None,
    **_kwargs: Any,
) -> int:
    """Nudges Miniflux to fetch the feeds whose per-feed interval has come round.

    This is not a second poller: Miniflux still performs every fetch, parse and deduplication, and
    the entries still reach Lumia by webhook. All this adds is the "when", which Miniflux has no
    per-feed setting for — its interval is instance-wide.

    One nudge per Miniflux feed, not per subscription: several readers can subscribe to the same
    feed, and refreshing it once serves all of them. A feed Miniflux rejects is logged and skipped
    rather than sinking the run, and is still marked as attempted so a permanently broken feed
    cannot be retried on every single tick.
    """
    async with worker_session() as session:
        due = await list_feeds_due_for_refresh(session, now=datetime.now(UTC))
        if not due:
            return 0

        refreshed: set[str] = set()
        for feed in due:
            if feed.external_feed_id in refreshed:
                continue
            refreshed.add(feed.external_feed_id)
            try:
                await refresh_feed(int(feed.external_feed_id), transport=transport)
            except (MinifluxApiError, httpx.HTTPError, ValueError):
                logger.warning("could not refresh feed %s on schedule", feed.id)

        await mark_refreshed(session, due)

    logger.info(
        "scheduled refresh nudged %d feed(s) for %d subscription(s)", len(refreshed), len(due)
    )
    return len(refreshed)
