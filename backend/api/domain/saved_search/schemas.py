from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SavedSearchCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    query: str = Field(min_length=2, max_length=200)
    feed_id: UUID | None = None
    folder_id: UUID | None = None
    alert: bool = False


class SavedSearchUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    alert: bool | None = None


class SavedSearchResponse(BaseModel):
    id: UUID
    name: str
    query: str
    feed_id: UUID | None
    folder_id: UUID | None
    alert: bool
    unread_count: int


class NotificationResponse(BaseModel):
    id: UUID
    saved_search_id: UUID
    saved_search_name: str
    article_id: UUID
    article_title: str
    read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    unread_count: int
    items: list[NotificationResponse]


class NotificationsMarkReadRequest(BaseModel):
    """Ids to mark read; leaving it out marks every unread notification."""

    ids: list[UUID] | None = Field(default=None, max_length=1000)
