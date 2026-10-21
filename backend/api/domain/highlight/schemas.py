from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

#: Generous for a paragraph a reader wants to keep, small enough that one row cannot hold a book.
MAX_QUOTE_LENGTH = 5000
MAX_CONTEXT_LENGTH = 200
MAX_NOTE_LENGTH = 2000


class HighlightCreateRequest(BaseModel):
    quote: str = Field(min_length=1, max_length=MAX_QUOTE_LENGTH)
    prefix: str = Field(default="", max_length=MAX_CONTEXT_LENGTH)
    suffix: str = Field(default="", max_length=MAX_CONTEXT_LENGTH)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class HighlightUpdateRequest(BaseModel):
    """`null` removes the note; the passage itself is never edited, only deleted and re-made."""

    note: str | None = Field(max_length=MAX_NOTE_LENGTH)


class HighlightResponse(BaseModel):
    id: UUID
    article_id: UUID
    article_title: str
    quote: str
    prefix: str
    suffix: str
    start_offset: int
    end_offset: int
    note: str | None
    created_at: datetime
