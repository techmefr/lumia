from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ArticleSummaryResponse(BaseModel):
    id: UUID
    feed_id: UUID
    author_id: UUID | None
    category_id: UUID | None
    title: str
    url: str
    summary: str | None
    published_at: datetime


class ArticleDetailResponse(ArticleSummaryResponse):
    content: str
