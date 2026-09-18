"""Shared article-list filtering, used by the article feed and by saved searches.

Saved searches are a name attached to the same filter set the reader already has in the article
list (folder, feed, author, category, keyword, free-text query) — extracting the predicate here is
what keeps a saved search literally "the same search, re-run" rather than a second implementation
that could drift from the first.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select

from api.domain.article.models import Article, ArticleKeyword
from api.domain.article.search_config import SEARCH_REGCONFIGS
from api.domain.feed.models import Feed


@dataclass(frozen=True)
class SearchFilters:
    """One reusable search, as both the article list and a saved search express it."""

    query: str | None = None
    folder_id: UUID | None = None
    feed_id: UUID | None = None
    author_id: UUID | None = None
    category_id: UUID | None = None
    keyword_id: UUID | None = None


def search_condition(q: str) -> ColumnElement[bool]:
    """Matches the generated `search_vector` column against a reader's search text.

    See `article/search_config.py`: the query text is parsed under every text-search configuration
    the index uses and OR-ed into a single tsquery, so one condition reaches every article language.
    """
    first, *rest = SEARCH_REGCONFIGS
    combined: ColumnElement[Any] = func.websearch_to_tsquery(first, q)
    for regconfig in rest:
        combined = combined.op("||")(func.websearch_to_tsquery(regconfig, q))
    return Article.search_vector.op("@@")(combined)


def apply_search_filters[RowT: tuple[Any, ...]](
    query: Select[RowT], filters: SearchFilters
) -> Select[RowT]:
    """Narrows an article query to one saved search's (or the live search bar's) filters.

    Generic over the selected row: the same predicate applies whether the query selects whole
    `Article` rows, a bare `Article.id` (ingestion-time matching) or a `count(...)` (the unread
    counter), since none of the filters below touch what is being selected, only what is matched.
    """
    if filters.folder_id is not None:
        query = query.where(Feed.folder_id == filters.folder_id)
    if filters.feed_id is not None:
        query = query.where(Article.feed_id == filters.feed_id)
    if filters.author_id is not None:
        query = query.where(Article.author_id == filters.author_id)
    if filters.category_id is not None:
        query = query.where(Article.category_id == filters.category_id)
    if filters.keyword_id is not None:
        query = query.join(ArticleKeyword, ArticleKeyword.article_id == Article.id).where(
            ArticleKeyword.keyword_id == filters.keyword_id
        )
    if filters.query is not None:
        query = query.where(search_condition(filters.query))
    return query


def base_query_for_user(user_id: UUID) -> Select[tuple[Article]]:
    return select(Article).join(Feed, Feed.id == Article.feed_id).where(Feed.user_id == user_id)


def matches_article(filters: SearchFilters, article_id: UUID, user_id: UUID) -> Select[tuple[UUID]]:
    """A query that returns `article_id` itself iff it satisfies `filters` for `user_id`.

    Used at ingestion time to check one freshly created article against a saved search, without
    scanning the rest of the table: the predicate is identical to the list one, just anchored to a
    single row.
    """
    query = apply_search_filters(
        select(Article.id)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Feed.user_id == user_id, Article.id == article_id),
        filters,
    )
    return query
