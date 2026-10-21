from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

MAX_TAG_LENGTH = 40


class TagNameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_TAG_LENGTH)

    @field_validator("name")
    @classmethod
    def _normalise(cls, value: str) -> str:
        collapsed = " ".join(value.split())
        if not collapsed:
            raise ValueError("a tag name cannot be blank")
        return collapsed


class TagRef(BaseModel):
    id: UUID
    name: str


class TagResponse(TagRef):
    article_count: int


class TagSuggestionResponse(BaseModel):
    name: str
    source: Literal["keyword", "used", "ai"]
