import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.import_progress import record_outcome, reset_counts
from api.domain.article.save_url_service import save_url
from api.domain.user.models import User
from worker.technical.content_extraction import (
    PageExtractor,
    PageFetchError,
    TrafilaturaPageExtractor,
)
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def import_reading_list(
    ctx: dict[Any, Any], user_id: str, import_id: str, urls: list[str]
) -> int:
    """Saves each link of an imported reading list as an article, one failure at a time.

    A dead or unreadable link is the normal case in a years-old Pocket export, so it is counted and
    skipped rather than aborting the rest. The fetch itself goes through the URL guard.
    """
    redis = ctx["redis"]
    extractor: PageExtractor = ctx.get("page_extractor") or TrafilaturaPageExtractor()
    await reset_counts(redis, import_id)

    saved = 0
    async with worker_session() as session:
        user = await _load_user(session, user_id)
        for url in urls:
            if user is None:
                await record_outcome(redis, import_id, saved=False)
                continue
            try:
                await save_url(session, user, url, page_extractor=extractor)
            except PageFetchError:
                await record_outcome(redis, import_id, saved=False)
                continue
            except SQLAlchemyError:
                # The rollback expires the user too, and a lazy reload under asyncio would raise.
                await session.rollback()
                logger.warning(
                    "reading list link could not be stored", extra={"import_id": import_id}
                )
                user = await _load_user(session, user_id)
                await record_outcome(redis, import_id, saved=False)
                continue
            saved += 1
            await record_outcome(redis, import_id, saved=True)
    return saved


async def _load_user(session: AsyncSession, user_id: str) -> User | None:
    user: User | None = await session.scalar(select(User).where(User.id == UUID(user_id)))
    return user
