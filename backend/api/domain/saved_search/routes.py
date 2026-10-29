from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.saved_search.exceptions import (
    SavedSearchNameTakenError,
    SavedSearchScopeNotFoundError,
)
from api.domain.saved_search.models import SavedSearch
from api.domain.saved_search.notification_service import (
    count_unread,
    list_notifications,
    mark_read,
)
from api.domain.saved_search.saved_search_service import (
    create_saved_search,
    delete_saved_search,
    list_saved_searches,
    unread_counts,
    update_saved_search,
)
from api.domain.saved_search.schemas import (
    NotificationListResponse,
    NotificationResponse,
    NotificationsMarkReadRequest,
    SavedSearchCreateRequest,
    SavedSearchResponse,
    SavedSearchUpdateRequest,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


def _to_response(search: SavedSearch, unread_count: int) -> SavedSearchResponse:
    return SavedSearchResponse(
        id=search.id,
        name=search.name,
        query=search.query,
        feed_id=search.feed_id,
        folder_id=search.folder_id,
        alert=search.alert,
        unread_count=unread_count,
    )


@router.get("/saved-searches", response_model=list[SavedSearchResponse])
async def get_saved_searches(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SavedSearchResponse]:
    searches = await list_saved_searches(session, user.id)
    counts = await unread_counts(session, user.id, searches)
    return [_to_response(search, counts[search.id]) for search in searches]


@router.post(
    "/saved-searches", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED
)
async def post_saved_search(
    payload: SavedSearchCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SavedSearchResponse:
    try:
        search = await create_saved_search(
            session,
            user.id,
            name=payload.name,
            query=payload.query,
            feed_id=payload.feed_id,
            folder_id=payload.folder_id,
            alert=payload.alert,
        )
    except SavedSearchScopeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except SavedSearchNameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc
    counts = await unread_counts(session, user.id, [search])
    return _to_response(search, counts[search.id])


@router.patch("/saved-searches/{search_id}", response_model=SavedSearchResponse)
async def patch_saved_search(
    search_id: UUID,
    payload: SavedSearchUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SavedSearchResponse:
    try:
        search = await update_saved_search(
            session, user.id, search_id, name=payload.name, alert=payload.alert
        )
    except SavedSearchNameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    counts = await unread_counts(session, user.id, [search])
    return _to_response(search, counts[search.id])


@router.delete("/saved-searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_saved_search(
    search_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if not await delete_saved_search(session, user.id, search_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NotificationListResponse:
    rows = await list_notifications(session, user.id, limit=limit, offset=offset)
    return NotificationListResponse(
        unread_count=await count_unread(session, user.id),
        items=[
            NotificationResponse(
                id=notification.id,
                saved_search_id=notification.saved_search_id,
                saved_search_name=search_name,
                article_id=notification.article_id,
                article_title=title,
                read=notification.read,
                created_at=notification.created_at,
            )
            for notification, search_name, title in rows
        ],
    )


@router.post("/notifications/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    payload: NotificationsMarkReadRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await mark_read(session, user.id, payload.ids)
