from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.models import Feed, Folder
from api.domain.feed.schemas import (
    FeedCreateRequest,
    FeedResponse,
    FolderCreateRequest,
    FolderResponse,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


def _to_folder_response(folder: Folder) -> FolderResponse:
    return FolderResponse(id=folder.id, name=folder.name)


@router.get("/folders", response_model=list[FolderResponse])
async def list_folders(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[FolderResponse]:
    folders = await session.scalars(select(Folder).where(Folder.user_id == user.id))
    return [_to_folder_response(folder) for folder in folders]


@router.post(
    "/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED
)
async def create_folder(
    payload: FolderCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FolderResponse:
    folder = Folder(user_id=user.id, name=payload.name)
    session.add(folder)
    await session.commit()
    return _to_folder_response(folder)


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


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feed(
    feed_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    feed = await session.scalar(
        select(Feed).where(Feed.id == feed_id, Feed.user_id == user.id)
    )
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(feed)
    await session.commit()
