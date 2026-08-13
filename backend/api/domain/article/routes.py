from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword
from api.domain.article.save_url_service import save_url
from api.domain.article.schemas import (
    ArticleDetailResponse,
    ArticleSummaryResponse,
    KeywordResponse,
    SaveUrlRequest,
)
from api.domain.feed.models import Feed
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.recommendation.read_service import fetch_read_article_ids
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session
from worker.technical.content_extraction import (
    PageExtractor,
    PageFetchError,
    get_page_extractor,
)

router = APIRouter()


def to_summary(article: Article, *, read: bool = False) -> ArticleSummaryResponse:
    return ArticleSummaryResponse(
        id=article.id,
        feed_id=article.feed_id,
        author_id=article.author_id,
        author_name=article.author.name if article.author else None,
        category_id=article.category_id,
        category_name=article.category.name if article.category else None,
        source_label=article.feed.title,
        title=article.title,
        url=article.url,
        summary=article.summary,
        image_url=article.image_url,
        published_at=article.published_at,
        read=read,
    )


async def to_summaries(
    session: AsyncSession, user_id: UUID, articles: list[Article]
) -> list[ArticleSummaryResponse]:
    read_ids = await fetch_read_article_ids(session, user_id, [article.id for article in articles])
    return [to_summary(article, read=article.id in read_ids) for article in articles]


def apply_unread_only(query: Select[tuple[Article]], user_id: UUID) -> Select[tuple[Article]]:
    """Keeps articles with no read feedback row for this user — absence of a row means unread."""
    read_rows = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user_id,
        UserArticleFeedback.article_id == Article.id,
        UserArticleFeedback.read.is_(True),
    )
    return query.where(~read_rows.exists())


@router.get("/articles", response_model=list[ArticleSummaryResponse])
async def list_articles(
    folder_id: UUID | None = Query(default=None),
    feed_id: UUID | None = Query(default=None),
    author_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    keyword_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None, min_length=2, max_length=200),
    unread_only: bool = Query(default=False),
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
    if author_id is not None:
        query = query.where(Article.author_id == author_id)
    if category_id is not None:
        query = query.where(Article.category_id == category_id)
    if keyword_id is not None:
        query = query.join(ArticleKeyword, ArticleKeyword.article_id == Article.id).where(
            ArticleKeyword.keyword_id == keyword_id
        )
    if q is not None:
        # ILIKE over content matches the stored HTML too, so a search term that happens to be a
        # tag or attribute name can hit. Accepted: the alternative is a tsvector column and a
        # migration to keep it in sync, which this corpus size doesn't justify yet.
        pattern = f"%{q}%"
        query = query.where(
            or_(
                Article.title.ilike(pattern),
                Article.summary.ilike(pattern),
                Article.content.ilike(pattern),
            )
        )
    if unread_only:
        query = apply_unread_only(query, user.id)
    query = query.order_by(Article.published_at.desc()).limit(limit).offset(offset)

    articles = list(await session.scalars(query))
    return await to_summaries(session, user.id, articles)


@router.post(
    "/articles/save-url",
    response_model=ArticleSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_article_url(
    payload: SaveUrlRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    page_extractor: PageExtractor = Depends(get_page_extractor),
) -> ArticleSummaryResponse:
    try:
        article = await save_url(session, user, payload.url, page_extractor=page_extractor)
    except PageFetchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc
    return to_summary(article)


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

    keywords = [
        KeywordResponse(id=link.keyword.id, term=link.keyword.term)
        for link in article.keyword_links
    ]
    read_ids = await fetch_read_article_ids(session, user.id, [article.id])

    return ArticleDetailResponse(
        **to_summary(article, read=article.id in read_ids).model_dump(),
        content=article.content,
        keywords=keywords,
    )
