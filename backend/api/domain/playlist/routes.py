from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.routes import to_summaries
from api.domain.playlist.exceptions import ArticleNotFoundError, PlaylistNotFoundError
from api.domain.playlist.models import Playlist
from api.domain.playlist.playlist_service import (
    add_article,
    get_playlist,
    remove_article,
    reorder,
    total_reading_minutes,
)
from api.domain.playlist.schemas import (
    PlaylistCreateRequest,
    PlaylistDetailResponse,
    PlaylistItemAddRequest,
    PlaylistReorderRequest,
    PlaylistSummaryResponse,
    PlaylistUpdateRequest,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


def _to_summary(playlist: Playlist) -> PlaylistSummaryResponse:
    return PlaylistSummaryResponse(
        id=playlist.id,
        name=playlist.name,
        item_count=len(playlist.items),
        total_reading_minutes=total_reading_minutes(playlist),
    )


async def _to_detail(
    session: AsyncSession, user_id: UUID, playlist: Playlist
) -> PlaylistDetailResponse:
    articles = await to_summaries(
        session, user_id, [item.article for item in playlist.items]
    )
    return PlaylistDetailResponse(id=playlist.id, name=playlist.name, articles=articles)


async def _load(session: AsyncSession, user_id: UUID, playlist_id: UUID) -> Playlist:
    try:
        return await get_playlist(session, user_id, playlist_id)
    except PlaylistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@router.get("/playlists", response_model=list[PlaylistSummaryResponse])
async def list_playlists(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[PlaylistSummaryResponse]:
    playlists = await session.scalars(
        select(Playlist).where(Playlist.user_id == user.id).order_by(Playlist.created_at)
    )
    return [_to_summary(playlist) for playlist in playlists]


@router.post(
    "/playlists", response_model=PlaylistSummaryResponse, status_code=status.HTTP_201_CREATED
)
async def create_playlist(
    payload: PlaylistCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistSummaryResponse:
    playlist = Playlist(user_id=user.id, name=payload.name)
    session.add(playlist)
    await session.commit()
    # `items` is unloaded on a freshly inserted instance; reading it would lazy-load under asyncio.
    await session.refresh(playlist, ["items"])
    return _to_summary(playlist)


@router.get("/playlists/{playlist_id}", response_model=PlaylistDetailResponse)
async def get_playlist_detail(
    playlist_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistDetailResponse:
    playlist = await _load(session, user.id, playlist_id)
    return await _to_detail(session, user.id, playlist)


@router.patch("/playlists/{playlist_id}", response_model=PlaylistSummaryResponse)
async def rename_playlist(
    playlist_id: UUID,
    payload: PlaylistUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistSummaryResponse:
    playlist = await _load(session, user.id, playlist_id)
    playlist.name = payload.name
    await session.commit()
    return _to_summary(playlist)


@router.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    playlist = await _load(session, user.id, playlist_id)
    await session.delete(playlist)
    await session.commit()


@router.post("/playlists/{playlist_id}/items", response_model=PlaylistDetailResponse)
async def add_playlist_item(
    playlist_id: UUID,
    payload: PlaylistItemAddRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistDetailResponse:
    try:
        playlist = await add_article(session, user.id, playlist_id, payload.article_id)
    except (PlaylistNotFoundError, ArticleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return await _to_detail(session, user.id, playlist)


@router.delete("/playlists/{playlist_id}/items/{article_id}", response_model=PlaylistDetailResponse)
async def remove_playlist_item(
    playlist_id: UUID,
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistDetailResponse:
    try:
        playlist = await remove_article(session, user.id, playlist_id, article_id)
    except (PlaylistNotFoundError, ArticleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return await _to_detail(session, user.id, playlist)


@router.put("/playlists/{playlist_id}/order", response_model=PlaylistDetailResponse)
async def reorder_playlist(
    playlist_id: UUID,
    payload: PlaylistReorderRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistDetailResponse:
    try:
        playlist = await reorder(session, user.id, playlist_id, payload.article_ids)
    except PlaylistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return await _to_detail(session, user.id, playlist)
