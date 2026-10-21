from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.filters import apply_unread_only
from api.domain.feed.models import Feed, Folder
from api.domain.recommendation.models import FilterMode
from api.domain.recommendation.relevance import load_rule_terms
from api.domain.saved_search.exceptions import (
    SavedSearchNameTakenError,
    SavedSearchScopeNotFoundError,
)
from api.domain.saved_search.matching import articles_matching
from api.domain.saved_search.models import AlertNotification, SavedSearch


async def list_saved_searches(session: AsyncSession, user_id: UUID) -> list[SavedSearch]:
    rows = await session.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user_id).order_by(SavedSearch.name)
    )
    return list(rows)


async def unread_counts(
    session: AsyncSession, user_id: UUID, searches: list[SavedSearch]
) -> dict[UUID, int]:
    if not searches:
        return {}
    muted = await load_rule_terms(session, user_id, FilterMode.MUTE)
    counts: dict[UUID, int] = {}
    for search in searches:
        unread = apply_unread_only(articles_matching(search, muted_terms=muted), user_id)
        counts[search.id] = (
            await session.scalar(select(func.count()).select_from(unread.subquery())) or 0
        )
    return counts


async def create_saved_search(
    session: AsyncSession,
    user_id: UUID,
    *,
    name: str,
    query: str,
    feed_id: UUID | None,
    folder_id: UUID | None,
    alert: bool,
) -> SavedSearch:
    await _ensure_scope_is_the_readers(session, user_id, feed_id=feed_id, folder_id=folder_id)
    search = SavedSearch(
        user_id=user_id,
        name=name.strip(),
        query=query.strip(),
        feed_id=feed_id,
        folder_id=folder_id,
        alert=alert,
    )
    session.add(search)
    await _commit_unique(session)
    return search


async def update_saved_search(
    session: AsyncSession,
    user_id: UUID,
    search_id: UUID,
    *,
    name: str | None,
    alert: bool | None,
) -> SavedSearch | None:
    search = await get_saved_search(session, user_id, search_id)
    if search is None:
        return None
    if name is not None:
        search.name = name.strip()
    if alert is not None:
        search.alert = alert
    await _commit_unique(session)
    return search


async def get_saved_search(
    session: AsyncSession, user_id: UUID, search_id: UUID
) -> SavedSearch | None:
    search: SavedSearch | None = await session.scalar(
        select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == user_id)
    )
    return search


async def delete_saved_search(session: AsyncSession, user_id: UUID, search_id: UUID) -> bool:
    search = await get_saved_search(session, user_id, search_id)
    if search is None:
        return False
    await remove_searches(session, [search.id])
    await session.commit()
    return True


async def delete_searches_scoped_to(
    session: AsyncSession, *, feed_id: UUID | None = None, folder_id: UUID | None = None
) -> None:
    """A search pinned to a feed or folder that is going away cannot keep its meaning.

    Dropping the scope instead would turn "rust in this blog" into "rust everywhere" behind the
    reader's back. The caller commits.
    """
    scope: ColumnElement[bool] = (
        SavedSearch.feed_id == feed_id
        if feed_id is not None
        else SavedSearch.folder_id == folder_id
    )
    ids = list(await session.scalars(select(SavedSearch.id).where(scope)))
    await remove_searches(session, ids)


async def remove_searches(session: AsyncSession, search_ids: list[UUID]) -> None:
    await session.execute(
        delete(AlertNotification).where(AlertNotification.saved_search_id.in_(search_ids))
    )
    await session.execute(delete(SavedSearch).where(SavedSearch.id.in_(search_ids)))


async def _ensure_scope_is_the_readers(
    session: AsyncSession, user_id: UUID, *, feed_id: UUID | None, folder_id: UUID | None
) -> None:
    if feed_id is not None:
        feed = await session.scalar(
            select(Feed.id).where(Feed.id == feed_id, Feed.user_id == user_id)
        )
        if feed is None:
            raise SavedSearchScopeNotFoundError
    if folder_id is not None:
        folder = await session.scalar(
            select(Folder.id).where(Folder.id == folder_id, Folder.user_id == user_id)
        )
        if folder is None:
            raise SavedSearchScopeNotFoundError


async def _commit_unique(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise SavedSearchNameTakenError from exc
