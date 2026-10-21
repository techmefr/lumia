from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.highlight import highlight_service
from api.domain.highlight.exceptions import ArticleNotFoundError, HighlightNotFoundError
from api.domain.highlight.models import Highlight
from api.domain.highlight.schemas import (
    HighlightCreateRequest,
    HighlightResponse,
    HighlightUpdateRequest,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


def _to_response(highlight: Highlight) -> HighlightResponse:
    return HighlightResponse(
        id=highlight.id,
        article_id=highlight.article_id,
        article_title=highlight.article.title,
        quote=highlight.quote,
        prefix=highlight.prefix,
        suffix=highlight.suffix,
        start_offset=highlight.start_offset,
        end_offset=highlight.end_offset,
        note=highlight.note,
        created_at=highlight.created_at,
    )


@router.get("/highlights", response_model=list[HighlightResponse])
async def list_highlights(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[HighlightResponse]:
    return [_to_response(item) for item in await highlight_service.list_all(session, user.id)]


@router.get("/articles/{article_id}/highlights", response_model=list[HighlightResponse])
async def list_article_highlights(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[HighlightResponse]:
    try:
        items = await highlight_service.list_for_article(session, user.id, article_id)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return [_to_response(item) for item in items]


@router.post(
    "/articles/{article_id}/highlights",
    response_model=HighlightResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_highlight(
    article_id: UUID,
    payload: HighlightCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> HighlightResponse:
    try:
        highlight = await highlight_service.create(session, user.id, article_id, payload)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return _to_response(highlight)


@router.patch("/highlights/{highlight_id}", response_model=HighlightResponse)
async def update_highlight(
    highlight_id: UUID,
    payload: HighlightUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> HighlightResponse:
    try:
        highlight = await highlight_service.update_note(
            session, user.id, highlight_id, payload.note
        )
    except HighlightNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return _to_response(highlight)


@router.delete("/highlights/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_highlight(
    highlight_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await highlight_service.delete(session, user.id, highlight_id)
    except HighlightNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
