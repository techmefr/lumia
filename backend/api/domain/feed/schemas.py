from uuid import UUID

from pydantic import BaseModel

from api.domain.feed.models import SourceType


class FolderCreateRequest(BaseModel):
    name: str


class FolderResponse(BaseModel):
    id: UUID
    name: str


class FeedCreateRequest(BaseModel):
    source_type: SourceType
    external_feed_id: str
    title: str
    url: str
    folder_id: UUID | None = None


class FeedAddByUrlRequest(BaseModel):
    url: str
    folder_id: UUID | None = None


class FolderUpdateRequest(BaseModel):
    name: str


class FeedUpdateRequest(BaseModel):
    """Both fields are optional; folder_id=None explicitly unfiles the feed, so the route has to
    distinguish 'not sent' from 'sent as null' via model_fields_set."""

    title: str | None = None
    folder_id: UUID | None = None


class UnreadCountsResponse(BaseModel):
    total: int
    feeds: dict[UUID, int]
    folders: dict[UUID, int]


class DiscoverSuggestionResponse(BaseModel):
    title: str
    url: str
    site_url: str
    description: str
    language: str
    topics: list[str]
    #: None when nothing is known about the reader yet, rather than a misleading 0.
    affinity: float | None


class FeedResponse(BaseModel):
    id: UUID
    folder_id: UUID | None
    source_type: SourceType
    external_feed_id: str
    title: str
    url: str
