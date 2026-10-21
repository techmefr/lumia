from datetime import date
from uuid import UUID

from pydantic import BaseModel


class DailyReading(BaseModel):
    day: date
    articles_read: int
    reading_minutes: int


class RankedSource(BaseModel):
    id: UUID
    name: str
    articles_read: int


class RankedKeyword(BaseModel):
    term: str
    articles_read: int


class FeedEngagement(BaseModel):
    """What a feed delivered against what was read of it, to decide which one to drop."""

    feed_id: UUID
    title: str
    received: int
    read: int
    ignored: int
    read_ratio: float


class FeedbackTotals(BaseModel):
    saved: int
    favorites: int
    liked: int
    disliked: int


class ReadingStatisticsResponse(BaseModel):
    period_days: int
    articles_read: int
    reading_minutes: int
    daily: list[DailyReading]
    top_feeds: list[RankedSource]
    top_authors: list[RankedSource]
    top_keywords: list[RankedKeyword]
    feed_engagement: list[FeedEngagement]
    totals: FeedbackTotals


class PopularArticle(BaseModel):
    title: str
    url: str
    readers: int


class PopularityResponse(BaseModel):
    period_days: int
    min_readers: int
    articles: list[PopularArticle]
