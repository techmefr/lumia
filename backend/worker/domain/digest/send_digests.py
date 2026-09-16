import logging
from datetime import UTC, datetime
from typing import Any

from api.domain.digest.digest_service import send_due_digests
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def send_reader_digests(
    ctx: dict[Any, Any], *_args: Any, now: datetime | None = None, **_kwargs: Any
) -> int:
    """Mails the periodic digest to every reader whose chosen hour has just come round.

    Runs every hour rather than once a night because readers live in different zones and pick
    their own hour; the per-reader period guard is what keeps an hourly job from being an hourly
    mail. `now` is injectable so tests can stand at a chosen wall clock.
    """
    moment = now or datetime.now(UTC)
    async with worker_session() as session:
        sent = await send_due_digests(session, now=moment)
    logger.info("sent %d reader digests", sent)
    return sent
