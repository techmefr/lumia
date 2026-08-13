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


class FeedResponse(BaseModel):
    id: UUID
    folder_id: UUID | None
    source_type: SourceType
    external_feed_id: str
    title: str
    url: str
