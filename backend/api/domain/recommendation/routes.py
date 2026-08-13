from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.article.schemas import ArticleSummaryResponse
from api.domain.recommendation.etincelle_service import list_etincelle
from api.domain.recommendation.feedback_service import apply_feedback
from api.domain.recommendation.saved_service import list_saved
from api.domain.recommendation.schemas import FeedbackRequest
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
    return [
        ArticleSummaryResponse(
            id=article.id,
            feed_id=article.feed_id,
            author_id=article.author_id,
            category_id=article.category_id,
            title=article.title,
            url=article.url,
            summary=article.summary,
            published_at=article.published_at,
        )
        for article in articles
    ]


@router.get("/articles/etincelle", response_model=list[ArticleSummaryResponse])
async def get_etincelle(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ArticleSummaryResponse]:
    ranked = await list_etincelle(session, user.id, limit=limit, offset=offset)
    return [
        ArticleSummaryResponse(
            id=article.id,
            feed_id=article.feed_id,
            author_id=article.author_id,
            category_id=article.category_id,
            title=article.title,
            url=article.url,
            summary=article.summary,
            published_at=article.published_at,
        )
        for article, _score in ranked
    ]


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

    await apply_feedback(session, user_id=user.id, article_id=article_id, vote=payload.vote)
