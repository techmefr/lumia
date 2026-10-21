from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.saved_search.models import AlertNotification, SavedSearch


async def list_notifications(
    session: AsyncSession, user_id: UUID, *, limit: int, offset: int
) -> list[tuple[AlertNotification, str, str]]:
    rows = await session.execute(
        select(AlertNotification, SavedSearch.name, Article.title)
        .join(SavedSearch, SavedSearch.id == AlertNotification.saved_search_id)
        .join(Article, Article.id == AlertNotification.article_id)
        .where(AlertNotification.user_id == user_id)
        .order_by(AlertNotification.created_at.desc(), AlertNotification.id)
        .limit(limit)
        .offset(offset)
    )
    return [(notification, search_name, title) for notification, search_name, title in rows]


async def count_unread(session: AsyncSession, user_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(AlertNotification)
            .where(AlertNotification.user_id == user_id, AlertNotification.read.is_(False))
        )
        or 0
    )


async def mark_read(session: AsyncSession, user_id: UUID, ids: list[UUID] | None) -> None:
    statement = (
        update(AlertNotification)
        .where(AlertNotification.user_id == user_id, AlertNotification.read.is_(False))
        .values(read=True)
    )
    if ids is not None:
        statement = statement.where(AlertNotification.id.in_(ids))
    await session.execute(statement)
    await session.commit()
