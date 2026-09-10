import logging
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.exceptions import FeedUnreachableError, FolderNotFoundError
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.feed.opml_parser import OpmlEntry, parse_opml
from api.domain.user.models import User
from api.technical.logging.external import (
    EXTERNAL_CALL_FAILED_EVENT,
    describe_error,
    redact_url,
)
from api.technical.net.url_guard import (
    BlockedUrlError,
    Resolver,
    ensure_public_http_url,
    resolve_with_system,
)
from worker.technical.connectors.miniflux_client import (
    MinifluxApiError,
    create_category,
    create_feed,
    get_feed,
    list_categories,
)

logger = logging.getLogger(__name__)


async def import_opml(
    session: AsyncSession,
    user: User,
    xml_bytes: bytes,
    *,
    miniflux_transport: httpx.AsyncBaseTransport | None = None,
    resolve: Resolver = resolve_with_system,
) -> list[Feed]:
    entries = parse_opml(xml_bytes)

    folder_cache: dict[str, Folder] = {}
    category_id_by_folder_name = {
        category.title: category.category_id
        for category in await list_categories(transport=miniflux_transport)
    }

    created_feeds: list[Feed] = []
    for entry in entries:
        existing_feed = await session.scalar(
            select(Feed).where(Feed.user_id == user.id, Feed.url == entry.url)
        )
        if existing_feed is not None:
            continue

        try:
            ensure_public_http_url(entry.url, resolve=resolve)
        except BlockedUrlError:
            # One hostile or malformed entry must not abort an import of a hundred good ones.
            continue

        folder = await _get_or_create_folder(session, user, entry.folder_name, folder_cache)
        try:
            external_feed_id = await _register_with_miniflux(
                session,
                entry,
                category_id_by_folder_name,
                transport=miniflux_transport,
            )
        except (MinifluxApiError, httpx.HTTPError) as exc:
            # An unreachable/invalid feed URL must not abort the rest of the batch —
            # the user still gets every other feed from their Feedly export.
            logger.warning(
                "opml entry skipped, its feed could not be registered",
                extra={
                    "event": EXTERNAL_CALL_FAILED_EVENT,
                    "service": "miniflux",
                    "operation": "import_opml_entry",
                    "url": redact_url(entry.url),
                    "error": describe_error(exc),
                },
            )
            continue

        feed = Feed(
            user_id=user.id,
            folder_id=folder.id if folder else None,
            source_type=SourceType.MINIFLUX,
            external_feed_id=external_feed_id,
            title=entry.title,
            url=entry.url,
        )
        session.add(feed)
        created_feeds.append(feed)

    await session.commit()
    return created_feeds


async def add_feed(
    session: AsyncSession,
    user: User,
    url: str,
    folder_id: UUID | None,
    *,
    miniflux_transport: httpx.AsyncBaseTransport | None = None,
    resolve: Resolver = resolve_with_system,
) -> Feed:
    ensure_public_http_url(url, resolve=resolve)

    folder: Folder | None = None
    if folder_id is not None:
        folder = await session.scalar(
            select(Folder).where(Folder.id == folder_id, Folder.user_id == user.id)
        )
        if folder is None:
            raise FolderNotFoundError

    category_id: int | None = None
    if folder is not None:
        categories = await list_categories(transport=miniflux_transport)
        matching = next((c for c in categories if c.title == folder.name), None)
        category_id = (
            matching.category_id
            if matching is not None
            else (await create_category(folder.name, transport=miniflux_transport)).category_id
        )

    try:
        miniflux_feed = await create_feed(
            url, category_id=category_id, transport=miniflux_transport
        )
        detail = await get_feed(miniflux_feed.feed_id, transport=miniflux_transport)
    except (MinifluxApiError, httpx.HTTPError) as exc:
        raise FeedUnreachableError from exc

    feed = Feed(
        user_id=user.id,
        folder_id=folder.id if folder else None,
        source_type=SourceType.MINIFLUX,
        external_feed_id=str(detail.feed_id),
        title=detail.title,
        url=url,
    )
    session.add(feed)
    await session.commit()
    return feed


async def _get_or_create_folder(
    session: AsyncSession,
    user: User,
    folder_name: str | None,
    folder_cache: dict[str, Folder],
) -> Folder | None:
    if folder_name is None:
        return None
    if folder_name in folder_cache:
        return folder_cache[folder_name]

    folder = await session.scalar(
        select(Folder).where(Folder.user_id == user.id, Folder.name == folder_name)
    )
    if folder is None:
        folder = Folder(user_id=user.id, name=folder_name)
        session.add(folder)
        await session.flush()
    folder_cache[folder_name] = folder
    return folder


async def _register_with_miniflux(
    session: AsyncSession,
    entry: OpmlEntry,
    category_id_by_folder_name: dict[str, int],
    *,
    transport: httpx.AsyncBaseTransport | None,
) -> str:
    existing_feed = await session.scalar(select(Feed).where(Feed.url == entry.url))
    if existing_feed is not None:
        return existing_feed.external_feed_id

    category_id: int | None = None
    if entry.folder_name is not None:
        category_id = category_id_by_folder_name.get(entry.folder_name)
        if category_id is None:
            category = await create_category(entry.folder_name, transport=transport)
            category_id = category.category_id
            category_id_by_folder_name[entry.folder_name] = category_id

    miniflux_feed = await create_feed(entry.url, category_id=category_id, transport=transport)
    return str(miniflux_feed.feed_id)
