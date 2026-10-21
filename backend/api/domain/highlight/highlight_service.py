from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed
from api.domain.highlight.exceptions import ArticleNotFoundError, HighlightNotFoundError
from api.domain.highlight.models import Highlight
from api.domain.highlight.schemas import HighlightCreateRequest


async def list_for_article(
    session: AsyncSession, user_id: UUID, article_id: UUID
) -> list[Highlight]:
    await _assert_article_belongs_to_user(session, user_id, article_id)
    result = await session.scalars(
        select(Highlight)
        .where(Highlight.user_id == user_id, Highlight.article_id == article_id)
        .order_by(Highlight.start_offset, Highlight.created_at)
    )
    return list(result)


async def list_all(session: AsyncSession, user_id: UUID) -> list[Highlight]:
    result = await session.scalars(
        select(Highlight)
        .where(Highlight.user_id == user_id)
        .order_by(Highlight.created_at.desc(), Highlight.id)
    )
    return list(result)


async def create(
    session: AsyncSession, user_id: UUID, article_id: UUID, payload: HighlightCreateRequest
) -> Highlight:
    await _assert_article_belongs_to_user(session, user_id, article_id)
    highlight = Highlight(user_id=user_id, article_id=article_id, **payload.model_dump())
    session.add(highlight)
    await session.commit()
    await session.refresh(highlight, ["article"])
    return highlight


async def update_note(
    session: AsyncSession, user_id: UUID, highlight_id: UUID, note: str | None
) -> Highlight:
    highlight = await _get_own(session, user_id, highlight_id)
    highlight.note = note
    await session.commit()
    await session.refresh(highlight, ["article"])
    return highlight


async def delete(session: AsyncSession, user_id: UUID, highlight_id: UUID) -> None:
    highlight = await _get_own(session, user_id, highlight_id)
    await session.delete(highlight)
    await session.commit()


async def _get_own(session: AsyncSession, user_id: UUID, highlight_id: UUID) -> Highlight:
    highlight = await session.scalar(
        select(Highlight).where(Highlight.id == highlight_id, Highlight.user_id == user_id)
    )
    if highlight is None:
        raise HighlightNotFoundError
    return highlight


async def _assert_article_belongs_to_user(
    session: AsyncSession, user_id: UUID, article_id: UUID
) -> None:
    owned = await session.scalar(
        select(Article.id)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Article.id == article_id, Feed.user_id == user_id)
    )
    if owned is None:
        raise ArticleNotFoundError
