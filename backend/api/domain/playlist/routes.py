from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.routes import to_summaries
from api.domain.article.scope import resolve_scope_article_ids
from api.domain.playlist.duration_service import build_for_duration
from api.domain.playlist.exceptions import (
    ArticleNotFoundError,
    BulkItemsFailedError,
    CannotShareWithOwnerError,
    MembershipNotFoundError,
    MemberUserNotFoundError,
    PlaylistForbiddenError,
    PlaylistNotFoundError,
)
from api.domain.playlist.member_service import revoke, share_with, usernames
from api.domain.playlist.models import Playlist, PlaylistRole
from api.domain.playlist.playlist_service import (
    add_article,
    get_playlist,
    list_accessible,
    remove_article,
    reorder,
    role_on,
    set_articles_present,
    total_reading_minutes,
)
from api.domain.playlist.schemas import (
    PlaylistBulkItemsRequest,
    PlaylistBulkItemsResponse,
    PlaylistCreateRequest,
    PlaylistDetailResponse,
    PlaylistForDurationRequest,
    PlaylistItemAddRequest,
    PlaylistItemAuthorship,
    PlaylistMemberResponse,
    PlaylistMembersResponse,
    PlaylistReorderRequest,
    PlaylistShareRequest,
    PlaylistSummaryResponse,
    PlaylistUpdateRequest,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


def _role(playlist: Playlist, user_id: UUID) -> PlaylistRole:
    role = role_on(playlist, user_id)
    if role is None:
        raise PlaylistNotFoundError
    return role


async def _to_summary(
    session: AsyncSession, user_id: UUID, playlist: Playlist
) -> PlaylistSummaryResponse:
    owner_names = await usernames(session, {playlist.user_id})
    return _summary(playlist, _role(playlist, user_id), owner_names[playlist.user_id])


def _summary(playlist: Playlist, role: PlaylistRole, owner_name: str) -> PlaylistSummaryResponse:
    return PlaylistSummaryResponse(
        id=playlist.id,
        name=playlist.name,
        role=role,
        owner_name=owner_name,
        item_count=len(playlist.items),
        total_reading_minutes=total_reading_minutes(playlist),
    )


async def _to_detail(
    session: AsyncSession, user_id: UUID, playlist: Playlist
) -> PlaylistDetailResponse:
    articles = await to_summaries(session, user_id, [item.article for item in playlist.items])
    adder_ids = {item.added_by_user_id for item in playlist.items if item.added_by_user_id}
    names = await usernames(session, adder_ids | {playlist.user_id})
    return PlaylistDetailResponse(
        id=playlist.id,
        name=playlist.name,
        role=_role(playlist, user_id),
        owner_name=names[playlist.user_id],
        articles=articles,
        authorship=[
            PlaylistItemAuthorship(
                article_id=item.article_id,
                added_by=names.get(item.added_by_user_id) if item.added_by_user_id else None,
            )
            for item in playlist.items
        ],
    )


async def _load(
    session: AsyncSession,
    user_id: UUID,
    playlist_id: UUID,
    needs: PlaylistRole = PlaylistRole.VIEWER,
) -> Playlist:
    try:
        return await get_playlist(session, user_id, playlist_id, needs)
    except PlaylistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except PlaylistForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from exc


async def _to_members(session: AsyncSession, playlist: Playlist) -> PlaylistMembersResponse:
    names = await usernames(session, {m.user_id for m in playlist.members} | {playlist.user_id})
    return PlaylistMembersResponse(
        owner_name=names[playlist.user_id],
        members=[
            PlaylistMemberResponse(
                user_id=member.user_id, username=names[member.user_id], role=member.role
            )
            for member in playlist.members
        ],
    )


@router.get("/playlists", response_model=list[PlaylistSummaryResponse])
async def list_playlists(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[PlaylistSummaryResponse]:
    playlists = await list_accessible(session, user.id)
    owner_names = await usernames(session, {playlist.user_id for playlist in playlists})
    return [
        _summary(playlist, _role(playlist, user.id), owner_names[playlist.user_id])
        for playlist in playlists
    ]


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
    await session.refresh(playlist, ["items", "members"])
    return await _to_summary(session, user.id, playlist)


@router.post(
    "/playlists/for-duration",
    response_model=PlaylistDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_playlist_for_duration(
    payload: PlaylistForDurationRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistDetailResponse:
    playlist = await build_for_duration(session, user.id, target_minutes=payload.target_minutes)
    return await _to_detail(session, user.id, playlist)


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
    playlist = await _load(session, user.id, playlist_id, PlaylistRole.OWNER)
    playlist.name = payload.name
    await session.commit()
    return await _to_summary(session, user.id, playlist)


@router.delete("/playlists/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    playlist = await _load(session, user.id, playlist_id, PlaylistRole.OWNER)
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
    except PlaylistForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from exc
    return await _to_detail(session, user.id, playlist)


@router.post("/playlists/{playlist_id}/items/bulk", response_model=PlaylistBulkItemsResponse)
async def bulk_playlist_items(
    playlist_id: UUID,
    payload: PlaylistBulkItemsRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistBulkItemsResponse:
    """Adds or removes a whole scope of articles, all of it or none of it."""
    article_ids = await resolve_scope_article_ids(
        session,
        user.id,
        article_ids=payload.article_ids,
        feed_id=payload.feed_id,
        folder_id=payload.folder_id,
    )
    try:
        moved = await set_articles_present(
            session, user.id, playlist_id, article_ids, present=payload.present
        )
    except PlaylistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except PlaylistForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from exc
    except BulkItemsFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="bulk_items_failed"
        ) from exc
    return PlaylistBulkItemsResponse(moved=len(moved), article_ids=moved)


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
    except PlaylistForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from exc
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
    except PlaylistForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from exc
    return await _to_detail(session, user.id, playlist)


@router.get("/playlists/{playlist_id}/members", response_model=PlaylistMembersResponse)
async def list_playlist_members(
    playlist_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistMembersResponse:
    playlist = await _load(session, user.id, playlist_id)
    return await _to_members(session, playlist)


@router.put("/playlists/{playlist_id}/members", response_model=PlaylistMembersResponse)
async def share_playlist(
    playlist_id: UUID,
    payload: PlaylistShareRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlaylistMembersResponse:
    """Grants or changes a role for an account of this instance, found by its email."""
    try:
        playlist = await share_with(
            session, user.id, playlist_id, email=payload.email, role=payload.role
        )
    except PlaylistNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except PlaylistForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from exc
    except MemberUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="member_user_not_found"
        ) from exc
    except CannotShareWithOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cannot_share_with_owner"
        ) from exc
    return await _to_members(session, playlist)


@router.delete(
    "/playlists/{playlist_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_playlist_member(
    playlist_id: UUID,
    member_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await revoke(session, user.id, playlist_id, member_id)
    except (PlaylistNotFoundError, MembershipNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except PlaylistForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN) from exc
