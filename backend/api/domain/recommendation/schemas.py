from uuid import UUID

from pydantic import BaseModel, model_validator

from api.domain.recommendation.models import Vote


class FeedbackRequest(BaseModel):
    sentiment: Vote | None = None
    saved: bool | None = None
    favorite: bool | None = None
    read: bool | None = None


class MarkReadRequest(BaseModel):
    """Marks a whole scope as read. Exactly one scope must be given, to keep 'mark all as read'
    from silently applying to every feed when the caller forgets the filter."""

    article_ids: list[UUID] | None = None
    feed_id: UUID | None = None
    folder_id: UUID | None = None
    read: bool = True

    @model_validator(mode="after")
    def check_single_scope(self) -> "MarkReadRequest":
        scopes = [self.article_ids is not None, self.feed_id is not None, self.folder_id is not None]
        if sum(scopes) != 1:
            raise ValueError("exactly one of article_ids, feed_id or folder_id is required")
        return self


class MarkReadResponse(BaseModel):
    updated: int
