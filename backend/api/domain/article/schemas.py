from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from api.domain.user.models import ReadingLang


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
    reading_minutes: int
    read: bool = False
    scroll_progress: float = 0.0
    # 0-100 affinity, 50 meaning "nothing learned about this one yet".
    relevance_score: int = 50


class ArticleDetailResponse(ArticleSummaryResponse):
    content: str
    keywords: list[KeywordResponse]


class SaveUrlRequest(BaseModel):
    url: str


class ReadingListImportStartedResponse(BaseModel):
    import_id: str
    total: int


class ReadingListImportProgressResponse(BaseModel):
    total: int
    saved: int
    failed: int
    finished: bool


class TranslateArticleRequest(BaseModel):
    target_lang: ReadingLang


class ArticleTranslationResponse(BaseModel):
    """A translation computed on demand and never stored: the article keeps its own language."""

    target_lang: ReadingLang
    title: str
    content: str


class ArticleShareStatusResponse(BaseModel):
    """Whether the article has a live link, and whether the instance allows making one."""

    enabled: bool
    shared: bool
    created_at: datetime | None


class ArticleShareCreatedResponse(BaseModel):
    """The only time the token is shown: the server keeps its hash, not the token."""

    token: str
    created_at: datetime


class PublicArticleResponse(BaseModel):
    """What a link opens: the article itself and nothing about the reader or the library.

    No feed, no account, no id of the article: the token is the only handle the visitor holds.
    """

    title: str
    content: str
    url: str
    published_at: datetime
    author_name: str | None
    image_url: str | None
    language: str
