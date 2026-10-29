import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article
from api.domain.feed.models import Feed
from api.domain.webhook.models import (
    DeliveryStatus,
    OutboundWebhook,
    WebhookDelivery,
    WebhookEvent,
)
from worker.technical.queue import get_arq_pool

logger = logging.getLogger(__name__)

DELIVER_JOB = "deliver_webhook"
QUEUE_UNAVAILABLE = "queue unavailable"

PoolFactory = Callable[[], Awaitable[Any]]


class EventPublisher:
    """Turns something a reader did into deliveries owed to the webhooks listening for it.

    The pool is resolved only once a delivery exists: most readers have no webhook, and an action
    as frequent as marking an article read must not open a queue connection for nothing. Publishing
    never raises into the caller, because a reader's save has to succeed whether or not their
    webhook endpoint, or the queue behind it, is up.
    """

    def __init__(self, pool_factory: PoolFactory = get_arq_pool) -> None:
        self._pool_factory = pool_factory

    async def publish(
        self,
        session: AsyncSession,
        user_id: UUID,
        event: WebhookEvent,
        article_ids: Sequence[UUID],
        *,
        playlist: tuple[UUID, str] | None = None,
    ) -> None:
        try:
            await self._publish(session, user_id, event, article_ids, playlist)
        except Exception:
            logger.exception("could not publish %s", event.value)

    async def _publish(
        self,
        session: AsyncSession,
        user_id: UUID,
        event: WebhookEvent,
        article_ids: Sequence[UUID],
        playlist: tuple[UUID, str] | None,
    ) -> None:
        if not article_ids:
            return
        listeners = [
            webhook
            for webhook in await session.scalars(
                select(OutboundWebhook).where(
                    OutboundWebhook.user_id == user_id, OutboundWebhook.active.is_(True)
                )
            )
            if event.value in webhook.events
        ]
        if not listeners:
            return
        articles = list(
            await session.scalars(
                select(Article)
                .join(Feed, Feed.id == Article.feed_id)
                .where(Article.id.in_(article_ids), Feed.user_id == user_id)
                .order_by(Article.id)
            )
        )

        deliveries: list[WebhookDelivery] = []
        for webhook in listeners:
            for article in articles:
                delivery_id = uuid4()
                deliveries.append(
                    WebhookDelivery(
                        id=delivery_id,
                        webhook_id=webhook.id,
                        event=event.value,
                        payload=_payload(delivery_id, event, article, playlist),
                    )
                )
        session.add_all(deliveries)
        await session.commit()

        try:
            pool = await self._pool_factory()
            for delivery in deliveries:
                await pool.enqueue_job(DELIVER_JOB, str(delivery.id))
        except Exception:
            logger.exception("could not queue webhook deliveries")
            for delivery in deliveries:
                delivery.status = DeliveryStatus.FAILED
                delivery.last_error = QUEUE_UNAVAILABLE
            await session.commit()


def _payload(
    delivery_id: UUID,
    event: WebhookEvent,
    article: Article,
    playlist: tuple[UUID, str] | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": str(delivery_id),
        "event": event.value,
        "occurred_at": datetime.now(UTC).isoformat(),
        "article": {"id": str(article.id), "title": article.title, "url": article.url},
    }
    if playlist is not None:
        payload["playlist"] = {"id": str(playlist[0]), "name": playlist[1]}
    return payload


def get_event_publisher() -> EventPublisher:
    return EventPublisher()
