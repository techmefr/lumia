from uuid import UUID

from pydantic import BaseModel, Field

from api.domain.article.schemas import ArticleSummaryResponse
from api.domain.article.scope import ArticleScopeRequest


class PlaylistCreateRequest(BaseModel):
    name: str


class PlaylistUpdateRequest(BaseModel):
    name: str


class PlaylistForDurationRequest(BaseModel):
    """The UI offers 12, 25 and 45 minutes; the range is wider so the API isn't tied to those."""

    target_minutes: int = Field(ge=5, le=240)


class PlaylistItemAddRequest(BaseModel):
    article_id: UUID


class PlaylistBulkItemsRequest(ArticleScopeRequest):
    """Puts a whole scope in or out of a playlist. `present` false is what an undo sends back."""

    present: bool = True


class PlaylistBulkItemsResponse(BaseModel):
    """`article_ids` are the ones that actually moved, so an undo reverts those and nothing else."""

    moved: int
    article_ids: list[UUID]


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
