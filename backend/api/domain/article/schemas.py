from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class KeywordResponse(BaseModel):
    id: UUID
    term: str


class ArticleSummaryResponse(BaseModel):
    id: UUID
    feed_id: UUID
    author_id: UUID | None
    author_name: str | None
    category_id: UUID | None
    category_name: str | None
    source_label: str
    title: str
    url: str
    summary: str | None
    image_url: str | None
    published_at: datetime


class ArticleDetailResponse(ArticleSummaryResponse):
    content: str
    keywords: list[KeywordResponse]
