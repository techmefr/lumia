from collections.abc import Sequence
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.recommendation.exceptions import BulkFeedbackFailedError
from api.domain.recommendation.models import UserArticleFeedback


class FeedbackAxis(StrEnum):
    """The axes a bulk action may touch, one per request.

    `sentiment`, `saved`, `favorite` and `read` are independent: a reader who favourites a
    selection has said nothing about having read it. Taking a single axis per call is what keeps a
    bulk action from quietly answering questions the reader never asked.
    """

    READ = "read"
    SAVED = "saved"
    FAVORITE = "favorite"


async def set_feedback_axis(
    session: AsyncSession,
    user_id: UUID,
    article_ids: Sequence[UUID],
    *,
    axis: FeedbackAxis,
    value: bool,
) -> list[UUID]:
    """Sets one axis over a batch and returns the ids whose value actually changed.

    Everything is staged and committed once: the batch either lands whole or not at all, so a
    failure halfway cannot leave a selection half-modified with nothing on screen saying which
    half. The changed ids are returned rather than a bare count because that is what an undo needs
    — reverting the whole selection would flip articles that already held the target value.
    """
    if not article_ids:
        return []

    try:
        existing = {
            row.article_id: row
            for row in await session.scalars(
                select(UserArticleFeedback).where(
                    UserArticleFeedback.user_id == user_id,
                    UserArticleFeedback.article_id.in_(article_ids),
                )
            )
        }

        changed: list[UUID] = []
        for article_id in article_ids:
            row = existing.get(article_id)
            if row is None:
                # A missing row is the default on every axis, which is false. Asking for false
                # there changes nothing, so no row is written for it.
                if value is False:
                    continue
                row = UserArticleFeedback(user_id=user_id, article_id=article_id)
                session.add(row)
            elif getattr(row, axis.value) == value:
                continue
            setattr(row, axis.value, value)
            changed.append(article_id)

        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise BulkFeedbackFailedError from exc

    return changed
