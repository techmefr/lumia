from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword
from api.domain.article.reading_time import estimate_reading_minutes
from api.domain.article.save_url_service import save_url
from api.domain.article.schemas import (
    ArticleDetailResponse,
    ArticleSummaryResponse,
    KeywordResponse,
    SaveUrlRequest,
)
from api.domain.feed.models import Feed
from api.domain.instance.exceptions import (
    AccountQuotaExceededError,
    InstanceNotProvisionedError,
)
from api.domain.instance.settings_service import get_instance
from api.domain.instance.usage_service import ensure_within_disk_quota
from api.domain.recommendation.models import FilterMode, UserArticleFeedback
from api.domain.recommendation.read_service import ReadState, fetch_read_state
from api.domain.recommendation.relevance import (
    load_rule_terms,
    matches_any_term,
    score_articles,
    to_relevance,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session
from worker.technical.content_extraction import (
    PageExtractor,
    PageFetchError,
    get_page_extractor,
)

router = APIRouter()

#: How many of the most recent articles are considered when the ranking or the muting has to
#: happen in Python. Deep pagination past this is recency-ordered only, which is what the UI does.
_RANKING_POOL = 500


def to_summary(
    article: Article, *, state: ReadState | None = None, relevance: int = 50
) -> ArticleSummaryResponse:
    state = state or ReadState()
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
        reading_minutes=estimate_reading_minutes(article.content),
        read=state.read,
        scroll_progress=state.scroll_progress,
        relevance_score=relevance,
    )


async def to_summaries(
    session: AsyncSession, user_id: UUID, articles: list[Article]
) -> list[ArticleSummaryResponse]:
    states = await fetch_read_state(session, user_id, [article.id for article in articles])
    raw = await score_articles(session, user_id, articles)
    return [
        to_summary(
            article,
            state=states.get(article.id),
            relevance=to_relevance(raw.get(article.id, 0.0)),
        )
        for article in articles
    ]


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
    sort: Literal["recent", "relevance"] = Query(default="recent"),
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
    query = query.order_by(Article.published_at.desc())

    muted = await load_rule_terms(session, user.id, FilterMode.MUTE)
    if sort == "relevance" or muted:
        # Both the muting and the relevance order are computed in Python, so the window has to be
        # applied after them. Bounded by the recency order above rather than left unbounded: a
        # reader's feed is measured in thousands of rows, and the tail is what nobody scrolls to.
        candidates = list(await session.scalars(query.limit(_RANKING_POOL)))
        if muted:
            candidates = [a for a in candidates if not matches_any_term(a, muted)]
        if sort == "relevance":
            raw = await score_articles(session, user.id, candidates)
            candidates.sort(key=lambda a: (raw.get(a.id, 0.0), a.published_at), reverse=True)
        articles = candidates[offset : offset + limit]
    else:
        articles = list(await session.scalars(query.limit(limit).offset(offset)))
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
        instance = await get_instance(session)
        await ensure_within_disk_quota(session, instance, user)
    except InstanceNotProvisionedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except AccountQuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Votre compte occupe {exc.used_mb} Mo sur les {exc.quota_mb} Mo autorisés : "
                "supprimez des articles avant d'en enregistrer un nouveau"
            ),
        ) from exc

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
    states = await fetch_read_state(session, user.id, [article.id])
    raw = await score_articles(session, user.id, [article])

    return ArticleDetailResponse(
        **to_summary(
            article,
            state=states.get(article.id),
            relevance=to_relevance(raw.get(article.id, 0.0)),
        ).model_dump(),
        content=article.content,
        keywords=keywords,
    )
