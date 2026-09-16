from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.models import Feed, SourceType
from worker.technical.connectors.miniflux_client import (
    MinifluxKnownFeed,
    get_feed,
    refresh_all_feeds,
    refresh_feed,
)

#: Fixed categories a reader can act on, in order of how confidently the message identifies them.
#: Never the provider's own message: that string is free text and not meant for the reader.
_REASON_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("certificate", "certificate"),
    ("tls", "certificate"),
    ("ssl", "certificate"),
    ("timed out", "unreachable"),
    ("timeout", "unreachable"),
    ("connection refused", "unreachable"),
    ("no such host", "unreachable"),
    ("name or service not known", "unreachable"),
    ("404", "not_found"),
    ("not found", "not_found"),
    ("403", "forbidden"),
    ("forbidden", "forbidden"),
    ("401", "forbidden"),
    ("unauthorized", "forbidden"),
    ("unable to parse", "unparsable"),
    ("unable to detect", "unparsable"),
    ("invalid character", "unparsable"),
)


def classify_error_reason(message: str) -> str:
    """Maps Miniflux's free-text parsing error onto a fixed, translatable category.

    Falls back to "unknown" rather than leaking the raw message: it can be arbitrarily long, and
    on some feed setups it embeds the feed url itself, query string included.
    """
    lowered = message.lower()
    for keyword, reason in _REASON_KEYWORDS:
        if keyword in lowered:
            return reason
    return "unknown"


def apply_feed_status(feed: Feed, *, error_count: int, error_message: str, now: datetime) -> None:
    """Updates a feed's own error status from what Miniflux reports for it right now.

    error_since is only set the moment the feed *becomes* broken, and kept untouched while it
    stays broken, so the reader sees how long the feed has been down rather than a timestamp reset
    on every sync.
    """
    was_broken = feed.error_count > 0
    feed.error_count = error_count
    if error_count == 0:
        feed.error_reason = None
        feed.error_since = None
        return
    feed.error_reason = classify_error_reason(error_message)
    if not was_broken:
        feed.error_since = now


async def sync_feed_statuses(
    session: AsyncSession, known_feeds: Iterable[MinifluxKnownFeed]
) -> int:
    """Applies Miniflux's current error status to every locally known feed it matches.

    One instance can serve many readers, so a single `GET /v1/feeds` call is reconciled against
    every Feed row at once instead of one Miniflux round trip per row.
    """
    by_external_id = {str(known.feed_id): known for known in known_feeds}
    if not by_external_id:
        return 0

    feeds: Sequence[Feed] = (
        await session.scalars(
            select(Feed).where(
                Feed.source_type == SourceType.MINIFLUX,
                Feed.external_feed_id.in_(by_external_id),
            )
        )
    ).all()

    now = datetime.now(UTC)
    for feed in feeds:
        known = by_external_id[feed.external_feed_id]
        apply_feed_status(
            feed,
            error_count=known.parsing_error_count,
            error_message=known.parsing_error_message,
            now=now,
        )
    await session.commit()
    return len(feeds)


async def refresh_feed_now(
    session: AsyncSession, feed: Feed, *, transport: httpx.AsyncBaseTransport | None
) -> None:
    """Asks Miniflux to fetch the feed right away, then pulls its fresh error status.

    A refresh Miniflux runs synchronously updates its own record immediately, so re-reading the
    feed straight after is enough — no need to wait for the next scheduled sync.

    What this does not do is produce articles: Miniflux hands new entries to Lumia over the
    webhook, which lands after this call has already returned. last_refreshed_at therefore records
    that a fetch was asked for, and the caller must not present it as articles having arrived.
    """
    now = datetime.now(UTC)
    await refresh_feed(int(feed.external_feed_id), transport=transport)
    detail = await get_feed(int(feed.external_feed_id), transport=transport)
    apply_feed_status(
        feed,
        error_count=detail.parsing_error_count,
        error_message=detail.parsing_error_message,
        now=now,
    )
    feed.last_refreshed_at = now
    await session.commit()


async def refresh_all_feeds_now(
    session: AsyncSession, user_id: UUID, *, transport: httpx.AsyncBaseTransport | None
) -> int:
    """Asks Miniflux to fetch everything it polls, and stamps this reader's feeds as requested.

    Miniflux refreshes per account, not per Lumia reader, so this is deliberately coarse: on a
    shared instance one reader's "refresh everything" fetches feeds that belong to others too.
    That is the reason the route above it is rate limited far more tightly than the single-feed one.

    No error status is re-read here. Miniflux queues this batch and returns before the fetches
    finish, so anything read straight after would be the state from before the refresh; the
    15-minute sync_feed_error_status cron is what settles it.
    """
    await refresh_all_feeds(transport=transport)
    now = datetime.now(UTC)
    feeds: Sequence[Feed] = (
        await session.scalars(
            select(Feed).where(Feed.user_id == user_id, Feed.source_type == SourceType.MINIFLUX)
        )
    ).all()
    for feed in feeds:
        feed.last_refreshed_at = now
    await session.commit()
    return len(feeds)
