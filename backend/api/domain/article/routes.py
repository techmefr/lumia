import logging
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.epub_export import EpubChapter, build_epub
from api.domain.article.exceptions import (
    ImportNotFoundError,
    InvalidReadingListError,
    ReadingListTooLargeError,
)
from api.domain.article.export_filename import attachment_header
from api.domain.article.import_progress import ProgressRedis, read_progress, start_progress
from api.domain.article.models import Article, ArticleKeyword
from api.domain.article.reading_list_parser import ReadingListSource, parse_reading_list
from api.domain.article.reading_time import estimate_reading_minutes
from api.domain.article.related_service import find_related_articles
from api.domain.article.save_url_service import save_url
from api.domain.article.schemas import (
    ArticleDetailResponse,
    ArticleSummaryResponse,
    ArticleTranslationResponse,
    KeywordResponse,
    ReadingListImportProgressResponse,
    ReadingListImportStartedResponse,
    SaveUrlRequest,
    TranslateArticleRequest,
)
from api.domain.article.search_config import SEARCH_REGCONFIGS
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
    score_articles,
    to_relevance,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.domain.user.providers import get_translator
from api.technical.db import get_db_session
from api.technical.net.image_fetcher import ImageFetcher, get_image_fetcher
from worker.technical.content_extraction import (
    PageExtractor,
    PageFetchError,
    get_page_extractor,
)
from worker.technical.html import strip_html
from worker.technical.queue import get_arq_pool
from worker.technical.translation.base import TranslationApiError, Translator

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_READING_LIST_BYTES = 5 * 1024 * 1024
_UPLOAD_CHUNK_BYTES = 64 * 1024
_IMPORT_JOB_TIMEOUT_SECONDS = 60 * 60

#: The smallest window of recent articles scored when the feed is sorted by relevance. A deeper
#: page widens it, so pagination never stops before the feed does.
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


def exclude_muted_terms(query: Select[tuple[Article]], terms: list[str]) -> Select[tuple[Article]]:
    """Drops the articles a mute rule matches, in SQL.

    Same reach as `matches_any_term` — the title and the summary, never the stored HTML — but done
    here so the window and the offset apply to what the reader actually gets. `summary` is nullable
    and a comparison against NULL is NULL, not false, so it is coalesced before matching: otherwise
    every article without a summary would be filtered out by the negation.
    """
    patterns = [f"%{term}%" for term in terms]
    return query.where(
        ~or_(
            *[Article.title.ilike(pattern) for pattern in patterns],
            *[func.coalesce(Article.summary, "").ilike(pattern) for pattern in patterns],
        )
    )


def _search_condition(q: str) -> ColumnElement[bool]:
    """Matches the generated `search_vector` column against the reader's search text.

    An article's vector is built under the configuration of its own `original_lang`, and a reader's
    library mixes languages, so a single query has to reach all of them: the query text is parsed
    under every configuration the index actually uses, and any match counts.

    The per-configuration queries are OR-ed together into one tsquery rather than compared with one
    `@@` each. Both forms return the same rows, but this one is a single operator against the GIN
    index instead of nine, which keeps widening the language coverage from costing nine index
    scans. Postgres tolerates a query text with nothing recognised under a given configuration
    (`websearch_to_tsquery` then returns an empty tsquery, which contributes nothing to the
    disjunction), so this never raises — it only narrows to whichever languages the terms parse as.
    """
    first, *rest = SEARCH_REGCONFIGS
    combined: ColumnElement[Any] = func.websearch_to_tsquery(first, q)
    for regconfig in rest:
        combined = combined.op("||")(func.websearch_to_tsquery(regconfig, q))
    return Article.search_vector.op("@@")(combined)


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
        query = query.where(_search_condition(q))
    if unread_only:
        query = apply_unread_only(query, user.id)
    query = query.order_by(Article.published_at.desc())

    muted = await load_rule_terms(session, user.id, FilterMode.MUTE)
    if muted:
        query = exclude_muted_terms(query, muted)

    if sort == "relevance":
        # The relevance order cannot be expressed in SQL, so a window of the most recent articles
        # is scored in Python and sliced. The window grows with the requested page rather than
        # being fixed: a fixed one ends the feed at its own size, which is not the end of the feed.
        pool = max(_RANKING_POOL, offset + limit)
        candidates = list(await session.scalars(query.limit(pool)))
        raw = await score_articles(session, user.id, candidates)
        candidates.sort(key=lambda a: (raw.get(a.id, 0.0), a.published_at), reverse=True)
        articles = candidates[offset : offset + limit]
    else:
        articles = list(await session.scalars(query.limit(limit).offset(offset)))
    return await to_summaries(session, user.id, articles)


async def _ensure_room_to_save(session: AsyncSession, user: User) -> None:
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
    await _ensure_room_to_save(session, user)

    try:
        article = await save_url(session, user, payload.url, page_extractor=page_extractor)
    except PageFetchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc
    return to_summary(article)


async def _read_capped(file: UploadFile) -> bytes:
    body = bytearray()
    while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
        body += chunk
        if len(body) > _MAX_READING_LIST_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    return bytes(body)


@router.post(
    "/articles/import-reading-list",
    response_model=ReadingListImportStartedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_reading_list(
    file: UploadFile,
    source: ReadingListSource = Form(),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    pool: Any = Depends(get_arq_pool),
) -> ReadingListImportStartedResponse:
    """Parses the export here, but fetches the pages in the worker: a Pocket list is thousands of
    links, far more than a request can wait for."""
    await _ensure_room_to_save(session, user)
    data = await _read_capped(file)
    try:
        urls = parse_reading_list(source, data)
    except InvalidReadingListError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc
    except ReadingListTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE) from exc

    import_id = uuid4().hex
    progress_store: ProgressRedis = pool
    await start_progress(progress_store, import_id, user.id, len(urls))
    if urls:
        await pool.enqueue_job(
            "import_reading_list",
            str(user.id),
            import_id,
            urls,
            _job_timeout=_IMPORT_JOB_TIMEOUT_SECONDS,
        )
    return ReadingListImportStartedResponse(import_id=import_id, total=len(urls))


@router.get(
    "/articles/import-reading-list/{import_id}",
    response_model=ReadingListImportProgressResponse,
)
async def get_reading_list_import_progress(
    import_id: str,
    user: User = Depends(get_current_user),
    pool: Any = Depends(get_arq_pool),
) -> ReadingListImportProgressResponse:
    progress_store: ProgressRedis = pool
    try:
        progress = await read_progress(progress_store, import_id, user.id)
    except ImportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return ReadingListImportProgressResponse.model_validate(progress)


async def load_own_article(session: AsyncSession, article_id: UUID, user: User) -> Article:
    article = await session.scalar(
        select(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Article.id == article_id, Feed.user_id == user.id)
    )
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return article


@router.get("/articles/{article_id}", response_model=ArticleDetailResponse)
async def get_article(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleDetailResponse:
    article = await load_own_article(session, article_id, user)

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


@router.get("/articles/{article_id}/related", response_model=list[ArticleSummaryResponse])
async def list_related_articles(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ArticleSummaryResponse]:
    article = await load_own_article(session, article_id, user)
    related = await find_related_articles(session, user.id, article)
    return await to_summaries(session, user.id, related)


@router.get("/articles/{article_id}/export.epub")
async def export_article_epub(
    article_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    images: ImageFetcher = Depends(get_image_fetcher),
) -> Response:
    article = await load_own_article(session, article_id, user)
    book = await build_epub(
        title=article.title,
        language=article.original_lang.value,
        chapters=[
            EpubChapter(
                title=article.title,
                author=article.author.name if article.author else None,
                url=article.url,
                published_at=article.published_at,
                html=article.content,
            )
        ],
        images=images,
    )
    return Response(
        content=book,
        media_type="application/epub+zip",
        headers={"Content-Disposition": attachment_header(article.title, "epub")},
    )


@router.post("/articles/{article_id}/translate", response_model=ArticleTranslationResponse)
async def translate_article(
    article_id: UUID,
    payload: TranslateArticleRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    translator: Translator | None = Depends(get_translator),
) -> ArticleTranslationResponse:
    """Translates one article on demand, leaving the stored one untouched.

    Unavailable rather than failed when the account has no provider or the provider does not cover
    the language: neither is a bug on either side, and the reader keeps the original.
    """
    article = await load_own_article(session, article_id, user)
    if translator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="no_translation_provider"
        )
    if not translator.supports(payload.target_lang.value):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="language_not_supported"
        )
    try:
        title = await translator.translate(article.title, target_lang=payload.target_lang.value)
        content = await translator.translate(
            strip_html(article.content), target_lang=payload.target_lang.value
        )
    except (TranslationApiError, httpx.HTTPError) as exc:
        # Logged for the operator, never relayed: the provider's own message is not ours to hand
        # back to a reader.
        logger.warning("on-demand translation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="translation_failed"
        ) from exc
    return ArticleTranslationResponse(target_lang=payload.target_lang, title=title, content=content)
