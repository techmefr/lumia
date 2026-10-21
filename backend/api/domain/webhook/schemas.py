from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from api.domain.webhook.models import DeliveryStatus, WebhookEvent


class WebhookCreateRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    events: list[WebhookEvent] = Field(min_length=1)


class WebhookUpdateRequest(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    events: list[WebhookEvent] | None = Field(default=None, min_length=1)
    active: bool | None = None


class WebhookResponse(BaseModel):
    id: UUID
    url: str
    events: list[WebhookEvent]
    active: bool
    created_at: datetime


class WebhookCreatedResponse(WebhookResponse):
    secret: str


class DeliveryResponse(BaseModel):
    id: UUID
    event: WebhookEvent
    status: DeliveryStatus
    attempts: int
    last_status_code: int | None
    last_error: str | None
    created_at: datetime
    delivered_at: datetime | None
