import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete

from api.domain.user.models import MagicLinkToken, RefreshToken
from config.maintenance import get_maintenance_config
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def purge_expired_tokens(ctx: dict[Any, Any], *_args: Any, **_kwargs: Any) -> int:
    """Deletes the login tokens whose lifetime ran out, well after it ran out.

    Nothing ever removed them, so the two tables grew for the lifetime of the instance. The grace
    period is what keeps this from erasing evidence: a token presented just after it lapsed is
    worth recognising as expired rather than as never issued.
    """
    config = get_maintenance_config()
    cutoff = datetime.now(UTC) - timedelta(days=config.token_purge_grace_days)

    async with worker_session() as session:
        purged = 0
        for model in (RefreshToken, MagicLinkToken):
            result = await session.execute(delete(model).where(model.expires_at < cutoff))
            purged += cast(CursorResult[Any], result).rowcount
        await session.commit()

    logger.info("purged %d login tokens expired before %s", purged, cutoff.isoformat())
    return purged
