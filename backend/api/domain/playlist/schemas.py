from uuid import UUID

from pydantic import BaseModel

from api.domain.article.schemas import ArticleSummaryResponse


class PlaylistCreateRequest(BaseModel):
    name: str


class PlaylistUpdateRequest(BaseModel):
    name: str


class PlaylistItemAddRequest(BaseModel):
    article_id: UUID


class PlaylistReorderRequest(BaseModel):
    """The full ordered list of article ids. Sending the whole order avoids the ambiguity of
    index-based moves when the client's copy is stale."""

    article_ids: list[UUID]


class PlaylistSummaryResponse(BaseModel):
    id: UUID
    name: str
    item_count: int
    total_reading_minutes: int


class PlaylistDetailResponse(BaseModel):
    id: UUID
    name: str
    articles: list[ArticleSummaryResponse]
