from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.recommendation.bulk_feedback_service import FeedbackAxis, set_feedback_axis
from api.domain.recommendation.models import UserArticleFeedback


@dataclass(frozen=True)
class ReadState:
    read: bool = False
    scroll_progress: float = 0.0


async def fetch_read_state(
    session: AsyncSession, user_id: UUID, article_ids: Sequence[UUID]
) -> dict[UUID, ReadState]:
    """Per-article read flag and reading position. A missing row means unread, position zero."""
    if not article_ids:
        return {}
    rows = await session.execute(
        select(
            UserArticleFeedback.article_id,
            UserArticleFeedback.read,
            UserArticleFeedback.scroll_progress,
        ).where(
            UserArticleFeedback.user_id == user_id,
            UserArticleFeedback.article_id.in_(article_ids),
        )
    )
    return {
        article_id: ReadState(read=read, scroll_progress=scroll_progress)
        for article_id, read, scroll_progress in rows
    }


async def mark_articles_read(
    session: AsyncSession, user_id: UUID, article_ids: Sequence[UUID], *, read: bool = True
) -> int:
    """Marks a batch as read/unread. Returns how many articles the scope covered."""
    await set_feedback_axis(session, user_id, article_ids, axis=FeedbackAxis.READ, value=read)
    return len(article_ids)
