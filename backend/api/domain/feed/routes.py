from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.discover_service import list_suggestions
from api.domain.feed.exceptions import FeedUnreachableError, FolderNotFoundError, InvalidOpmlError
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.feed.opml_service import add_feed, import_opml
from api.domain.feed.schemas import (
    DiscoverSuggestionResponse,
    FeedAddByUrlRequest,
    FeedCreateRequest,
    FeedResponse,
    FeedUpdateRequest,
    FolderCreateRequest,
    FolderResponse,
    FolderUpdateRequest,
    UnreadCountsResponse,
)
from api.domain.feed.unread_service import count_unread
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session
from api.technical.net.url_guard import BlockedUrlError, Resolver, get_url_resolver
from worker.technical.connectors.miniflux_client import (
    MinifluxApiError,
    get_feed_icon,
    get_miniflux_transport,
)

router = APIRouter()

_MAX_OPML_BYTES = 2 * 1024 * 1024
_UPLOAD_CHUNK_BYTES = 64 * 1024


def _to_folder_response(folder: Folder) -> FolderResponse:
    return FolderResponse(id=folder.id, name=folder.name)


@router.get("/folders", response_model=list[FolderResponse])
async def list_folders(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[FolderResponse]:
    folders = await session.scalars(select(Folder).where(Folder.user_id == user.id))
    return [_to_folder_response(folder) for folder in folders]


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FolderCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FolderResponse:
    folder = Folder(user_id=user.id, name=payload.name)
    session.add(folder)
    await session.commit()
    return _to_folder_response(folder)


@router.patch("/folders/{folder_id}", response_model=FolderResponse)
async def rename_folder(
    folder_id: UUID,
    payload: FolderUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FolderResponse:
    folder = await session.scalar(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user.id)
    )
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    folder.name = payload.name
    await session.commit()
    return _to_folder_response(folder)


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    folder = await session.scalar(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user.id)
    )
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Deleting a folder must not take its feeds (and their articles) with it — unfile them.
    await session.execute(update(Feed).where(Feed.folder_id == folder.id).values(folder_id=None))
    await session.delete(folder)
    await session.commit()


def _to_feed_response(feed: Feed) -> FeedResponse:
    return FeedResponse(
        id=feed.id,
        folder_id=feed.folder_id,
        source_type=feed.source_type,
        external_feed_id=feed.external_feed_id,
        title=feed.title,
        url=feed.url,
    )


@router.get("/feeds", response_model=list[FeedResponse])
async def list_feeds(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[FeedResponse]:
    feeds = await session.scalars(select(Feed).where(Feed.user_id == user.id))
    return [_to_feed_response(feed) for feed in feeds]


@router.get("/feeds/unread-counts", response_model=UnreadCountsResponse)
async def get_unread_counts(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UnreadCountsResponse:
    counts = await count_unread(session, user.id)
    return UnreadCountsResponse(total=counts.total, feeds=counts.feeds, folders=counts.folders)


@router.get("/feeds/discover", response_model=list[DiscoverSuggestionResponse])
async def discover_feeds(
    limit: int = Query(default=6, ge=1, le=20),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[DiscoverSuggestionResponse]:
    ranked = await list_suggestions(session, user.id, limit=limit)
    return [
        DiscoverSuggestionResponse(
            title=entry.title,
            url=entry.url,
            site_url=entry.site_url,
            description=entry.description,
            language=entry.language,
            topics=list(entry.topics),
            # A pool with no votes behind it would show a column of zeroes; say "unknown" instead.
            affinity=round(affinity, 2) if affinity > 0 else None,
        )
        for entry, affinity in ranked
    ]


@router.post("/feeds", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(
    payload: FeedCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeedResponse:
    feed = Feed(
        user_id=user.id,
        folder_id=payload.folder_id,
        source_type=payload.source_type,
        external_feed_id=payload.external_feed_id,
        title=payload.title,
        url=payload.url,
    )
    session.add(feed)
    await session.commit()
    return _to_feed_response(feed)


@router.post("/feeds/add-by-url", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def add_feed_by_url(
    payload: FeedAddByUrlRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    transport: httpx.AsyncBaseTransport | None = Depends(get_miniflux_transport),
    resolve: Resolver = Depends(get_url_resolver),
) -> FeedResponse:
    try:
        feed = await add_feed(
            session,
            user,
            payload.url,
            payload.folder_id,
            miniflux_transport=transport,
            resolve=resolve,
        )
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except (FeedUnreachableError, BlockedUrlError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc
    return _to_feed_response(feed)


async def _read_capped(file: UploadFile) -> bytes:
    """Reads an upload in chunks, refusing one that goes over the cap.

    A subscription export is a list of URLs, so a couple of megabytes is already generous — and
    reading first, checking after, would mean holding whatever was sent in memory before deciding
    it was too big.
    """
    body = bytearray()
    while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
        body += chunk
        if len(body) > _MAX_OPML_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    return bytes(body)


@router.post("/feeds/import-opml", response_model=list[FeedResponse])
async def import_opml_feeds(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    transport: httpx.AsyncBaseTransport | None = Depends(get_miniflux_transport),
    resolve: Resolver = Depends(get_url_resolver),
) -> list[FeedResponse]:
    xml_bytes = await _read_capped(file)
    try:
        feeds = await import_opml(
            session, user, xml_bytes, miniflux_transport=transport, resolve=resolve
        )
    except InvalidOpmlError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc
    return [_to_feed_response(feed) for feed in feeds]


@router.get("/feeds/{feed_id}/icon")
async def get_feed_icon_image(
    feed_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    transport: httpx.AsyncBaseTransport | None = Depends(get_miniflux_transport),
) -> Response:
    """Proxies the feed's icon: Miniflux sits on the internal network and needs its own
    credentials, so the browser can't fetch it directly."""
    feed = await session.scalar(select(Feed).where(Feed.id == feed_id, Feed.user_id == user.id))
    if feed is None or feed.source_type is not SourceType.MINIFLUX:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        icon = await get_feed_icon(int(feed.external_feed_id), transport=transport)
    except (MinifluxApiError, httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    if icon is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return Response(
        content=icon.data,
        media_type=icon.mime_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.patch("/feeds/{feed_id}", response_model=FeedResponse)
async def update_feed(
    feed_id: UUID,
    payload: FeedUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeedResponse:
    feed = await session.scalar(select(Feed).where(Feed.id == feed_id, Feed.user_id == user.id))
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if payload.title is not None:
        feed.title = payload.title
    if "folder_id" in payload.model_fields_set:
        if payload.folder_id is not None:
            folder = await session.scalar(
                select(Folder).where(Folder.id == payload.folder_id, Folder.user_id == user.id)
            )
            if folder is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        # The move stays local: Miniflux keeps the category it was registered under, which only
        # matters for a future re-import, never for what Lumia displays.
        feed.folder_id = payload.folder_id

    await session.commit()
    return _to_feed_response(feed)


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    feed = await session.scalar(select(Feed).where(Feed.id == feed_id, Feed.user_id == user.id))
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(feed)
    await session.commit()
