from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.article.schemas import ArticleDetailResponse, ArticleSummaryResponse
from api.domain.feed.models import Feed
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()


def _to_summary(article: Article) -> ArticleSummaryResponse:
    return ArticleSummaryResponse(
        id=article.id,
        feed_id=article.feed_id,
        author_id=article.author_id,
        category_id=article.category_id,
        title=article.title,
        url=article.url,
        summary=article.summary,
        published_at=article.published_at,
    )


@router.get("/articles", response_model=list[ArticleSummaryResponse])
async def list_articles(
    folder_id: UUID | None = Query(default=None),
    feed_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ArticleSummaryResponse]:
    query = select(Article).join(Feed, Feed.id == Article.feed_id).where(Feed.user_id == user.id)
    if folder_id is not None:
        query = query.where(Feed.folder_id == folder_id)
    if feed_id is not None:
        query = query.where(Article.feed_id == feed_id)
    query = query.order_by(Article.published_at.desc()).limit(limit).offset(offset)

    articles = await session.scalars(query)
    return [_to_summary(article) for article in articles]


@router.get("/articles/{article_id}", response_model=ArticleDetailResponse)
async def get_article(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleDetailResponse:
    article = await session.scalar(
        select(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Article.id == article_id, Feed.user_id == user.id)
    )
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return ArticleDetailResponse(
        **_to_summary(article).model_dump(),
        content=article.content,
    )
