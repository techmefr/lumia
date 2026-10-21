import logging
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete

from api.domain.export.models import ExportJob
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def purge_expired_exports(ctx: dict[Any, Any], *_args: Any, **_kwargs: Any) -> int:
    """Deletes the exported files whose day is over, the bytes with the row."""
    async with worker_session() as session:
        result = await session.execute(
            delete(ExportJob).where(ExportJob.expires_at < datetime.now(UTC))
        )
        await session.commit()
    purged = cast(CursorResult[Any], result).rowcount
    logger.info("purged %d expired exports", purged)
    return purged
