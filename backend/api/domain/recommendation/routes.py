from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.article.routes import to_summaries
from api.domain.article.schemas import ArticleSummaryResponse
from api.domain.recommendation.etincelle_service import list_etincelle
from api.domain.recommendation.favorite_service import list_favorites
from api.domain.recommendation.feedback_service import apply_feedback
from api.domain.recommendation.filter_rule_service import add_rule, delete_rule, list_rules
from api.domain.recommendation.read_service import mark_articles_read, resolve_scope_article_ids
from api.domain.recommendation.saved_service import list_saved
from api.domain.recommendation.schemas import (
    FeedbackRequest,
    FilterRuleCreateRequest,
    FilterRuleResponse,
    MarkReadRequest,
    MarkReadResponse,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


@router.get("/articles/saved", response_model=list[ArticleSummaryResponse])
async def get_saved_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ArticleSummaryResponse]:
    articles = await list_saved(session, user.id, limit=limit, offset=offset)
    return await to_summaries(session, user.id, articles)


@router.get("/articles/favorites", response_model=list[ArticleSummaryResponse])
async def get_favorite_articles(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ArticleSummaryResponse]:
    articles = await list_favorites(session, user.id, limit=limit, offset=offset)
    return await to_summaries(session, user.id, articles)


@router.get("/articles/etincelle", response_model=list[ArticleSummaryResponse])
async def get_etincelle(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ArticleSummaryResponse]:
    ranked = await list_etincelle(session, user.id, limit=limit, offset=offset)
    return await to_summaries(session, user.id, [article for article, _score in ranked])


@router.post("/articles/mark-read", response_model=MarkReadResponse)
async def mark_read(
    payload: MarkReadRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MarkReadResponse:
    article_ids = await resolve_scope_article_ids(
        session,
        user.id,
        article_ids=payload.article_ids,
        feed_id=payload.feed_id,
        folder_id=payload.folder_id,
    )
    updated = await mark_articles_read(session, user.id, article_ids, read=payload.read)
    return MarkReadResponse(updated=updated)


@router.post("/articles/{article_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def send_feedback(
    article_id: UUID,
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    updates = payload.model_dump(exclude_unset=True)
    await apply_feedback(session, user_id=user.id, article_id=article_id, **updates)


@router.get("/filter-rules", response_model=list[FilterRuleResponse])
async def get_filter_rules(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[FilterRuleResponse]:
    rules = await list_rules(session, user.id)
    return [FilterRuleResponse(id=r.id, term=r.term, mode=r.mode) for r in rules]


@router.post(
    "/filter-rules", response_model=FilterRuleResponse, status_code=status.HTTP_201_CREATED
)
async def create_filter_rule(
    payload: FilterRuleCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FilterRuleResponse:
    rule = await add_rule(session, user.id, term=payload.term, mode=payload.mode)
    return FilterRuleResponse(id=rule.id, term=rule.term, mode=rule.mode)


@router.delete("/filter-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_filter_rule(
    rule_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if not await delete_rule(session, user.id, rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
