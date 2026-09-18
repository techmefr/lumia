from uuid import UUID

from pydantic import BaseModel, Field


class SavedSearchCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    query: str | None = Field(default=None, min_length=2, max_length=200)
    folder_id: UUID | None = None
    feed_id: UUID | None = None
    author_id: UUID | None = None
    category_id: UUID | None = None
    keyword_id: UUID | None = None
    is_alert: bool = False


class SavedSearchUpdateRequest(BaseModel):
    """Every field is optional: a rename should not force the caller to resend the filters."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    query: str | None = Field(default=None, min_length=2, max_length=200)
    folder_id: UUID | None = None
    feed_id: UUID | None = None
    author_id: UUID | None = None
    category_id: UUID | None = None
    keyword_id: UUID | None = None
    is_alert: bool | None = None


class SavedSearchResponse(BaseModel):
    id: UUID
    name: str
    query: str | None
    folder_id: UUID | None
    feed_id: UUID | None
    author_id: UUID | None
    category_id: UUID | None
    keyword_id: UUID | None
    is_alert: bool
    unread_count: int
