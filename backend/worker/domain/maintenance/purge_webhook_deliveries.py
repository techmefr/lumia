import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, delete

from api.domain.webhook.models import DeliveryStatus, WebhookDelivery
from config.maintenance import get_maintenance_config
from worker.technical.db import worker_session

logger = logging.getLogger(__name__)


async def purge_old_webhook_deliveries(ctx: dict[Any, Any], *_args: Any, **_kwargs: Any) -> int:
    config = get_maintenance_config()
    cutoff = datetime.now(UTC) - timedelta(days=config.webhook_delivery_retention_days)

    async with worker_session() as session:
        result = await session.execute(
            delete(WebhookDelivery).where(
                WebhookDelivery.created_at < cutoff,
                WebhookDelivery.status != DeliveryStatus.PENDING,
            )
        )
        await session.commit()

    purged = cast(CursorResult[Any], result).rowcount
    logger.info("purged %d webhook deliveries created before %s", purged, cutoff.isoformat())
    return purged
