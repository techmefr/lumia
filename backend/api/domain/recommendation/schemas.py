from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from api.domain.recommendation.models import FilterMode, Vote


class FeedbackRequest(BaseModel):
    sentiment: Vote | None = None
    saved: bool | None = None
    favorite: bool | None = None
    read: bool | None = None
    scroll_progress: float | None = Field(default=None, ge=0.0, le=1.0)


class MarkReadRequest(BaseModel):
    """Marks a whole scope as read. Exactly one scope must be given, to keep 'mark all as read'
    from silently applying to every feed when the caller forgets the filter. `all` still has to be
    passed explicitly and true, rather than inferred from every other field being empty, so a
    client that simply forgot to set a scope gets rejected instead of wiping every feed."""

    article_ids: list[UUID] | None = None
    feed_id: UUID | None = None
    folder_id: UUID | None = None
    all: bool = False
    read: bool = True

    @model_validator(mode="after")
    def check_single_scope(self) -> "MarkReadRequest":
        scopes = [
            self.article_ids is not None,
            self.feed_id is not None,
            self.folder_id is not None,
            self.all,
        ]
        if sum(scopes) != 1:
            raise ValueError("exactly one of article_ids, feed_id, folder_id or all is required")
        return self


class MarkReadResponse(BaseModel):
    updated: int


class FilterRuleCreateRequest(BaseModel):
    term: str = Field(min_length=2, max_length=80)
    mode: FilterMode


class FilterRuleResponse(BaseModel):
    id: UUID
    term: str
    mode: FilterMode
