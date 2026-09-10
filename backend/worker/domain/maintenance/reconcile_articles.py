import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from arq import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from config.maintenance import get_maintenance_config
from worker.technical.connectors.base import RawArticle
from worker.technical.connectors.miniflux_client import list_recent_entries
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def reconcile_recent_articles(
    ctx: dict[Any, Any],
    *_args: Any,
    transport: httpx.AsyncBaseTransport | None = None,
    **_kwargs: Any,
) -> int:
    """Re-enqueues recent Miniflux entries that never made it into the database.

    A webhook can be lost for reasons nothing in the app can prevent — the API restarting mid-post,
    a network blip, a signature refused after a secret rotation — and the article is then missing
    with nobody the wiser. Polling a bounded window closes that hole, and doubles as the recovery
    for an enrichment that exhausted its retries: the next pass simply queues it again.
    """
    config = get_maintenance_config()
    since = datetime.now(UTC) - timedelta(hours=config.reconciliation_window_hours)
    entries = await list_recent_entries(
        published_after=since, limit=config.reconciliation_max_entries, transport=transport
    )

    async with worker_session() as session:
        missing = await _missing_articles(session, entries)

    # arq hands its own pool to a scheduled job in the context; reaching back into
    # worker.technical.queue for one would only add an import cycle with the schedule itself.
    pool: ArqRedis = ctx["redis"]
    for article in missing:
        await pool.enqueue_job("enrich_article", article)
    logger.info(
        "reconciliation queued %d of %d recent entries since %s",
        len(missing),
        len(entries),
        since.isoformat(),
    )
    return len(missing)


async def _missing_articles(
    session: AsyncSession, entries: Sequence[RawArticle]
) -> list[RawArticle]:
    if not entries:
        return []

    # Only entries of a feed somebody subscribes to: enrichment resolves the feed rows itself and
    # does nothing when there are none, so queueing the rest would be an hourly no-op forever.
    subscribed = set(
        await session.scalars(
            select(Feed.external_feed_id).where(
                Feed.source_type == SourceType.MINIFLUX,
                Feed.external_feed_id.in_({entry.feed_external_id for entry in entries}),
            )
        )
    )
    stored = set(
        await session.scalars(
            select(Article.external_entry_id)
            .join(Feed, Article.feed_id == Feed.id)
            .where(
                Feed.source_type == SourceType.MINIFLUX,
                Article.external_entry_id.in_({entry.external_entry_id for entry in entries}),
            )
        )
    )
    return [
        entry
        for entry in entries
        if entry.feed_external_id in subscribed and entry.external_entry_id not in stored
    ]
