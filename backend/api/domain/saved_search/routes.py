from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.search_filters import SearchFilters
from api.domain.saved_search.models import SavedSearch
from api.domain.saved_search.saved_search_service import (
    count_unread_matches,
    create_saved_search,
    delete_saved_search,
    get_saved_search,
    list_saved_searches,
    update_saved_search,
)
from api.domain.saved_search.schemas import (
    SavedSearchCreateRequest,
    SavedSearchResponse,
    SavedSearchUpdateRequest,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


async def _to_response(session: AsyncSession, saved_search: SavedSearch) -> SavedSearchResponse:
    unread_count = await count_unread_matches(session, saved_search)
    return SavedSearchResponse(
        id=saved_search.id,
        name=saved_search.name,
        query=saved_search.query,
        folder_id=saved_search.folder_id,
        feed_id=saved_search.feed_id,
        author_id=saved_search.author_id,
        category_id=saved_search.category_id,
        keyword_id=saved_search.keyword_id,
        is_alert=saved_search.is_alert,
        unread_count=unread_count,
    )


@router.get("/saved-searches", response_model=list[SavedSearchResponse])
async def get_saved_searches(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SavedSearchResponse]:
    saved_searches = await list_saved_searches(session, user.id)
    return [await _to_response(session, saved_search) for saved_search in saved_searches]


@router.post(
    "/saved-searches", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED
)
async def create_search(
    payload: SavedSearchCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SavedSearchResponse:
    saved_search = await create_saved_search(
        session,
        user.id,
        name=payload.name,
        filters=SearchFilters(
            query=payload.query,
            folder_id=payload.folder_id,
            feed_id=payload.feed_id,
            author_id=payload.author_id,
            category_id=payload.category_id,
            keyword_id=payload.keyword_id,
        ),
        is_alert=payload.is_alert,
    )
    return await _to_response(session, saved_search)


@router.patch("/saved-searches/{saved_search_id}", response_model=SavedSearchResponse)
async def update_search(
    saved_search_id: UUID,
    payload: SavedSearchUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SavedSearchResponse:
    saved_search = await get_saved_search(session, user.id, saved_search_id)
    if saved_search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    updates = payload.model_dump(exclude_unset=True)
    saved_search = await update_saved_search(session, saved_search, **updates)
    return await _to_response(session, saved_search)


@router.delete("/saved-searches/{saved_search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_search(
    saved_search_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if not await delete_saved_search(session, user.id, saved_search_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
