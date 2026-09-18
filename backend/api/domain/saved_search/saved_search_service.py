from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.article.search_filters import (
    SearchFilters,
    apply_search_filters,
    base_query_for_user,
)
from api.domain.feed.models import Feed
from api.domain.recommendation.read_service import ReadState, fetch_read_state
from api.domain.saved_search.models import SavedSearch


def _filters_of(saved_search: SavedSearch) -> SearchFilters:
    return SearchFilters(
        query=saved_search.query,
        folder_id=saved_search.folder_id,
        feed_id=saved_search.feed_id,
        author_id=saved_search.author_id,
        category_id=saved_search.category_id,
        keyword_id=saved_search.keyword_id,
    )


async def list_saved_searches(session: AsyncSession, user_id: UUID) -> list[SavedSearch]:
    rows = await session.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user_id).order_by(SavedSearch.name)
    )
    return list(rows)


async def get_saved_search(
    session: AsyncSession, user_id: UUID, saved_search_id: UUID
) -> SavedSearch | None:
    query = select(SavedSearch).where(
        SavedSearch.id == saved_search_id, SavedSearch.user_id == user_id
    )
    result: SavedSearch | None = await session.scalar(query)
    return result


async def create_saved_search(
    session: AsyncSession,
    user_id: UUID,
    *,
    name: str,
    filters: SearchFilters,
    is_alert: bool,
) -> SavedSearch:
    saved_search = SavedSearch(
        user_id=user_id,
        name=name,
        query=filters.query,
        folder_id=filters.folder_id,
        feed_id=filters.feed_id,
        author_id=filters.author_id,
        category_id=filters.category_id,
        keyword_id=filters.keyword_id,
        is_alert=is_alert,
    )
    session.add(saved_search)
    await session.commit()
    await session.refresh(saved_search)
    return saved_search


_UNSET: Any = object()

_FILTER_FIELDS = ("query", "folder_id", "feed_id", "author_id", "category_id", "keyword_id")


async def update_saved_search(
    session: AsyncSession,
    saved_search: SavedSearch,
    *,
    name: str = _UNSET,
    is_alert: bool = _UNSET,
    **filter_updates: Any,
) -> SavedSearch:
    """Applies only the fields the caller actually sent.

    Filters are passed as loose kwargs rather than a `SearchFilters` so that omitting one, e.g.
    renaming a saved search without resending its filters, is expressible: `SearchFilters` itself
    has no way to distinguish "unset" from "cleared to None".
    """
    if name is not _UNSET:
        saved_search.name = name
    if is_alert is not _UNSET:
        saved_search.is_alert = is_alert
    for field in _FILTER_FIELDS:
        if field in filter_updates:
            setattr(saved_search, field, filter_updates[field])
    await session.commit()
    await session.refresh(saved_search)
    return saved_search


async def delete_saved_search(session: AsyncSession, user_id: UUID, saved_search_id: UUID) -> bool:
    saved_search = await get_saved_search(session, user_id, saved_search_id)
    if saved_search is None:
        return False
    await session.delete(saved_search)
    await session.commit()
    return True


async def run_saved_search(
    session: AsyncSession, saved_search: SavedSearch, *, limit: int, offset: int
) -> list[Article]:
    """Re-runs a saved search exactly as `GET /articles` would, most recent first."""
    query = apply_search_filters(
        base_query_for_user(saved_search.user_id), _filters_of(saved_search)
    )
    query = query.order_by(Article.published_at.desc()).limit(limit).offset(offset)
    return list(await session.scalars(query))


async def count_unread_matches(session: AsyncSession, saved_search: SavedSearch) -> int:
    """How many currently-unread articles this saved search would return, the counter the reader
    sees next to it — the same signal an unread-per-feed count already gives for a feed."""
    query = apply_search_filters(
        select(func.count(Article.id.distinct()))
        .select_from(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Feed.user_id == saved_search.user_id),
        _filters_of(saved_search),
    )
    total = await session.scalar(query) or 0
    if total == 0:
        return 0
    # Read state is not expressible as a plain filter (absence of a feedback row means unread), so
    # unlike the other filters it is applied by loading ids rather than folded into the count query.
    articles = list(
        await session.scalars(
            apply_search_filters(
                base_query_for_user(saved_search.user_id), _filters_of(saved_search)
            )
        )
    )
    states: dict[UUID, ReadState] = await fetch_read_state(
        session, saved_search.user_id, [article.id for article in articles]
    )
    return sum(1 for article in articles if not states.get(article.id, ReadState()).read)
