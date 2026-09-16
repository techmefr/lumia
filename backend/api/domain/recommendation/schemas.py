from uuid import UUID

from pydantic import BaseModel, Field

from api.domain.article.scope import ArticleScopeRequest
from api.domain.recommendation.bulk_feedback_service import FeedbackAxis
from api.domain.recommendation.models import FilterMode, Vote


class FeedbackRequest(BaseModel):
    sentiment: Vote | None = None
    saved: bool | None = None
    favorite: bool | None = None
    read: bool | None = None
    scroll_progress: float | None = Field(default=None, ge=0.0, le=1.0)


class MarkReadRequest(ArticleScopeRequest):
    """Marks a whole scope as read. The one-scope rule comes from `ArticleScopeRequest`."""

    read: bool = True


class MarkReadResponse(BaseModel):
    updated: int


class BulkFeedbackRequest(ArticleScopeRequest):
    """One axis, one value, one scope.

    The axis is named rather than derived from a set of optional flags: a request can therefore
    not carry `read` and `favorite` at once, and a bulk action stays something the reader can
    describe in a single sentence — and undo in one.
    """

    axis: FeedbackAxis
    value: bool = True


class BulkFeedbackResponse(BaseModel):
    """`changed_article_ids` holds only the articles that did not already have the target value,
    which is exactly what an undo must revert."""

    updated: int
    changed_article_ids: list[UUID]


class FilterRuleCreateRequest(BaseModel):
    term: str = Field(min_length=2, max_length=80)
    mode: FilterMode


class FilterRuleResponse(BaseModel):
    id: UUID
    term: str
    mode: FilterMode
