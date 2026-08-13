from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed
from api.domain.recommendation.models import UserArticleFeedback


async def fetch_read_article_ids(
    session: AsyncSession, user_id: UUID, article_ids: Sequence[UUID]
) -> set[UUID]:
    if not article_ids:
        return set()
    rows = await session.scalars(
        select(UserArticleFeedback.article_id).where(
            UserArticleFeedback.user_id == user_id,
            UserArticleFeedback.article_id.in_(article_ids),
            UserArticleFeedback.read.is_(True),
        )
    )
    return set(rows)


async def resolve_scope_article_ids(
    session: AsyncSession,
    user_id: UUID,
    *,
    article_ids: Sequence[UUID] | None = None,
    feed_id: UUID | None = None,
    folder_id: UUID | None = None,
) -> list[UUID]:
    """Expands a mark-read scope into article ids, always restricted to this user's own feeds."""
    query = (
        select(Article.id)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Feed.user_id == user_id)
    )
    if article_ids is not None:
        query = query.where(Article.id.in_(article_ids))
    if feed_id is not None:
        query = query.where(Article.feed_id == feed_id)
    if folder_id is not None:
        query = query.where(Feed.folder_id == folder_id)
    return list(await session.scalars(query))


async def mark_articles_read(
    session: AsyncSession, user_id: UUID, article_ids: Sequence[UUID], *, read: bool = True
) -> int:
    """Marks a batch as read/unread, inserting the missing feedback rows. Returns the row count."""
    if not article_ids:
        return 0

    existing = {
        row.article_id: row
        for row in await session.scalars(
            select(UserArticleFeedback).where(
                UserArticleFeedback.user_id == user_id,
                UserArticleFeedback.article_id.in_(article_ids),
            )
        )
    }
    for article_id in article_ids:
        row = existing.get(article_id)
        if row is None:
            row = UserArticleFeedback(user_id=user_id, article_id=article_id)
            session.add(row)
        row.read = read

    await session.commit()
    return len(article_ids)
