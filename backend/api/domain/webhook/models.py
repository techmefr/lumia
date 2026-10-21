from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class WebhookEvent(StrEnum):
    ARTICLE_SAVED = "article.saved"
    ARTICLE_FAVORITED = "article.favorited"
    PLAYLIST_ARTICLE_ADDED = "playlist.article_added"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class OutboundWebhook(Base, TimestampMixin):
    """An address a reader wants told about what they do in Lumia.

    The signing secret is stored encrypted rather than hashed: unlike a login token it has to be
    read back to sign every delivery. It is returned once, at creation, and never again.
    """

    __tablename__ = "outbound_webhooks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str]
    secret_encrypted: Mapped[str]
    events: Mapped[list[str]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(default=True)


class WebhookDelivery(Base, TimestampMixin):
    """One event owed to one webhook.

    The row is the answer to "did it arrive": a delivery that gives up ends FAILED with its last
    error instead of vanishing from the queue.
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    webhook_id: Mapped[UUID] = mapped_column(ForeignKey("outbound_webhooks.id"), index=True)
    event: Mapped[str]
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    status: Mapped[DeliveryStatus] = mapped_column(default=DeliveryStatus.PENDING)
    attempts: Mapped[int] = mapped_column(default=0)
    last_status_code: Mapped[int | None] = mapped_column(default=None)
    last_error: Mapped[str | None] = mapped_column(default=None)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
