"""The feeds the Miniflux instance carries, offered to a reader who subscribes to none of them.

Lumia is often pointed at a Miniflux that has been polling for years. Those feeds are invisible to
a reader until a `feeds` row exists for their account, and re-adding them by URL one at a time is
the only path otherwise.
"""

from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.exceptions import FeedUnreachableError
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.feed.opml_service import get_or_create_folder
from api.domain.user.models import User
from worker.technical.connectors.miniflux_client import (
    MinifluxApiError,
    MinifluxKnownFeed,
    list_feeds,
)


@dataclass(frozen=True)
class InstanceFeed:
    external_feed_id: str
    title: str
    url: str
    #: The Miniflux category, which becomes the folder the feed is filed into once attached.
    category: str | None


async def _known_feeds(transport: httpx.AsyncBaseTransport | None) -> list[MinifluxKnownFeed]:
    try:
        return await list_feeds(transport=transport)
    except (MinifluxApiError, httpx.HTTPError) as exc:
        raise FeedUnreachableError from exc


async def _subscribed_external_ids(session: AsyncSession, user: User) -> set[str]:
    rows = await session.scalars(
        select(Feed.external_feed_id).where(
            Feed.user_id == user.id, Feed.source_type == SourceType.MINIFLUX
        )
    )
    return set(rows)


async def list_instance_feeds(
    session: AsyncSession,
    user: User,
    *,
    miniflux_transport: httpx.AsyncBaseTransport | None = None,
) -> list[InstanceFeed]:
    """Everything the instance polls that this reader is not subscribed to yet."""
    subscribed = await _subscribed_external_ids(session, user)
    return [
        InstanceFeed(
            external_feed_id=str(known.feed_id),
            title=known.title,
            url=known.feed_url,
            category=known.category_title,
        )
        for known in await _known_feeds(miniflux_transport)
        if str(known.feed_id) not in subscribed
    ]


async def attach_instance_feeds(
    session: AsyncSession,
    user: User,
    external_feed_ids: list[str],
    *,
    miniflux_transport: httpx.AsyncBaseTransport | None = None,
) -> list[Feed]:
    """Subscribes the reader to feeds the instance already carries, reusing their Miniflux id.

    An id the instance does not carry is skipped rather than fatal: the list it came from is a
    snapshot, and a feed deleted in Miniflux meanwhile must not cost the reader the whole batch.
    """
    known_by_id = {str(known.feed_id): known for known in await _known_feeds(miniflux_transport)}
    subscribed = await _subscribed_external_ids(session, user)

    folder_cache: dict[str, Folder] = {}
    attached: list[Feed] = []
    for external_feed_id in external_feed_ids:
        known = known_by_id.get(external_feed_id)
        if known is None or external_feed_id in subscribed:
            continue

        folder = await get_or_create_folder(session, user, known.category_title, folder_cache)
        feed = Feed(
            user_id=user.id,
            folder_id=folder.id if folder else None,
            source_type=SourceType.MINIFLUX,
            external_feed_id=external_feed_id,
            title=known.title,
            url=known.feed_url,
        )
        session.add(feed)
        subscribed.add(external_feed_id)
        attached.append(feed)

    await session.commit()
    return attached
