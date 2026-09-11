import logging
from typing import Any

import httpx

from api.domain.feed.feed_status_service import sync_feed_statuses
from worker.technical.connectors.miniflux_client import list_feeds
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def sync_feed_error_status(
    ctx: dict[Any, Any],
    *_args: Any,
    transport: httpx.AsyncBaseTransport | None = None,
    **_kwargs: Any,
) -> int:
    """Mirrors Miniflux's own parsing-error counters onto every feed row that matches one.

    Miniflux notices a feed has broken on its own, but that knowledge stays on its side until
    something asks — this is what makes it show up for the reader instead of staying invisible.
    """
    known_feeds = await list_feeds(transport=transport)
    async with worker_session() as session:
        updated = await sync_feed_statuses(session, known_feeds)
    logger.info("feed status sync updated %d feed(s) of %d known", updated, len(known_feeds))
    return updated
