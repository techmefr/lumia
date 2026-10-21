from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import ColumnElement, Date, Integer, Numeric, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword, Author, Keyword
from api.domain.digest.schedule import reader_zone
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback, Vote
from api.domain.recommendation.statistics_schemas import (
    DailyReading,
    FeedbackTotals,
    FeedEngagement,
    PopularArticle,
    PopularityResponse,
    RankedKeyword,
    RankedSource,
    ReadingStatisticsResponse,
)
from api.domain.user.models import User

#: A popularity row says how many readers opened an article. Below this, the count would let one
#: reader be picked out by whoever knows what the others did not read, so the row is not shown.
POPULARITY_MIN_READERS = 3

_TOP_LIMIT = 5
_ENGAGEMENT_LIMIT = 20
_POPULAR_LIMIT = 10
_WORDS_PER_MINUTE = 200


def _reading_minutes_expression() -> ColumnElement[int]:
    """Mirrors estimate_reading_minutes in SQL so the sum is one aggregate, not a loop of rows."""
    words = func.cardinality(
        func.regexp_split_to_array(
            func.btrim(func.regexp_replace(Article.content, "<[^>]*>", " ", "g")), r"\s+"
        )
    )
    return cast(
        func.greatest(1, func.round(cast(words, Numeric) / _WORDS_PER_MINUTE)),
        Integer,
    )


def _read_since(user_id: UUID, since: datetime) -> list[ColumnElement[bool]]:
    return [
        UserArticleFeedback.user_id == user_id,
        UserArticleFeedback.read.is_(True),
        UserArticleFeedback.read_at >= since,
    ]


async def get_reading_statistics(
    session: AsyncSession, user: User, *, days: int, now: datetime | None = None
) -> ReadingStatisticsResponse:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)
    zone = reader_zone(user.digest_timezone)

    local_day = cast(func.timezone(zone.key, UserArticleFeedback.read_at), Date)
    daily_rows = await session.execute(
        select(local_day, func.count(), func.sum(_reading_minutes_expression()))
        .select_from(UserArticleFeedback)
        .join(Article, Article.id == UserArticleFeedback.article_id)
        .where(*_read_since(user.id, since))
        .group_by(local_day)
    )
    by_day = {row[0]: (int(row[1]), int(row[2] or 0)) for row in daily_rows}
    daily = [
        DailyReading(
            day=day,
            articles_read=by_day.get(day, (0, 0))[0],
            reading_minutes=by_day.get(day, (0, 0))[1],
        )
        for day in _days_ending(now.astimezone(zone).date(), days)
    ]

    return ReadingStatisticsResponse(
        period_days=days,
        articles_read=sum(entry.articles_read for entry in daily),
        reading_minutes=sum(entry.reading_minutes for entry in daily),
        daily=daily,
        top_feeds=await _top_feeds(session, user.id, since),
        top_authors=await _top_authors(session, user.id, since),
        top_keywords=await _top_keywords(session, user.id, since),
        feed_engagement=await _feed_engagement(session, user.id, since),
        totals=await _totals(session, user.id),
    )


def _days_ending(last: date, count: int) -> Sequence[date]:
    return [last - timedelta(days=offset) for offset in range(count - 1, -1, -1)]


async def _top_feeds(session: AsyncSession, user_id: UUID, since: datetime) -> list[RankedSource]:
    read_count = func.count()
    rows = await session.execute(
        select(Feed.id, Feed.title, read_count)
        .select_from(UserArticleFeedback)
        .join(Article, Article.id == UserArticleFeedback.article_id)
        .join(Feed, Feed.id == Article.feed_id)
        .where(*_read_since(user_id, since))
        .group_by(Feed.id, Feed.title)
        .order_by(read_count.desc(), Feed.title)
        .limit(_TOP_LIMIT)
    )
    return [RankedSource(id=row[0], name=row[1], articles_read=row[2]) for row in rows]


async def _top_authors(session: AsyncSession, user_id: UUID, since: datetime) -> list[RankedSource]:
    read_count = func.count()
    rows = await session.execute(
        select(Author.id, Author.name, read_count)
        .select_from(UserArticleFeedback)
        .join(Article, Article.id == UserArticleFeedback.article_id)
        .join(Author, Author.id == Article.author_id)
        .where(*_read_since(user_id, since))
        .group_by(Author.id, Author.name)
        .order_by(read_count.desc(), Author.name)
        .limit(_TOP_LIMIT)
    )
    return [RankedSource(id=row[0], name=row[1], articles_read=row[2]) for row in rows]


async def _top_keywords(
    session: AsyncSession, user_id: UUID, since: datetime
) -> list[RankedKeyword]:
    read_count = func.count()
    rows = await session.execute(
        select(Keyword.term, read_count)
        .select_from(UserArticleFeedback)
        .join(ArticleKeyword, ArticleKeyword.article_id == UserArticleFeedback.article_id)
        .join(Keyword, Keyword.id == ArticleKeyword.keyword_id)
        .where(*_read_since(user_id, since))
        .group_by(Keyword.term)
        .order_by(read_count.desc(), Keyword.term)
        .limit(_TOP_LIMIT)
    )
    return [RankedKeyword(term=row[0], articles_read=row[1]) for row in rows]


async def _feed_engagement(
    session: AsyncSession, user_id: UUID, since: datetime
) -> list[FeedEngagement]:
    received = func.count(Article.id)
    read = func.count(UserArticleFeedback.article_id)
    rows = await session.execute(
        select(Feed.id, Feed.title, received, read)
        .select_from(Feed)
        .join(Article, and_(Article.feed_id == Feed.id, Article.published_at >= since))
        .outerjoin(
            UserArticleFeedback,
            and_(
                UserArticleFeedback.article_id == Article.id,
                UserArticleFeedback.user_id == user_id,
                UserArticleFeedback.read.is_(True),
            ),
        )
        .where(Feed.user_id == user_id, Feed.source_type != SourceType.MANUAL)
        .group_by(Feed.id, Feed.title)
        .order_by(cast(read, Numeric) / received, received.desc(), Feed.title)
        .limit(_ENGAGEMENT_LIMIT)
    )
    return [
        FeedEngagement(
            feed_id=row[0],
            title=row[1],
            received=row[2],
            read=row[3],
            ignored=row[2] - row[3],
            read_ratio=round(row[3] / row[2], 2),
        )
        for row in rows
    ]


async def _totals(session: AsyncSession, user_id: UUID) -> FeedbackTotals:
    row = (
        await session.execute(
            select(
                func.count().filter(UserArticleFeedback.saved.is_(True)),
                func.count().filter(UserArticleFeedback.favorite.is_(True)),
                func.count().filter(UserArticleFeedback.sentiment == Vote.LIKE),
                func.count().filter(UserArticleFeedback.sentiment == Vote.DISLIKE),
            ).where(UserArticleFeedback.user_id == user_id)
        )
    ).one()
    return FeedbackTotals(saved=row[0], favorites=row[1], liked=row[2], disliked=row[3])


async def get_popular_articles(
    session: AsyncSession, *, days: int, now: datetime | None = None
) -> PopularityResponse:
    """Articles several readers of the instance opened, identified by canonical url.

    Every account owns its feeds and so its own copy of an article; the canonical url is what says
    two copies are the same piece. Only a title, a url and a count leave this query, never a
    reader, and a count under the threshold is dropped rather than rounded.
    """
    since = (now or datetime.now(UTC)) - timedelta(days=days)
    readers = func.count(func.distinct(UserArticleFeedback.user_id))
    rows = await session.execute(
        select(func.min(Article.title), func.min(Article.url), readers)
        .select_from(UserArticleFeedback)
        .join(Article, Article.id == UserArticleFeedback.article_id)
        .where(UserArticleFeedback.read.is_(True), UserArticleFeedback.read_at >= since)
        .group_by(Article.canonical_url)
        .having(readers >= POPULARITY_MIN_READERS)
        .order_by(readers.desc(), func.min(Article.title))
        .limit(_POPULAR_LIMIT)
    )
    return PopularityResponse(
        period_days=days,
        min_readers=POPULARITY_MIN_READERS,
        articles=[PopularArticle(title=row[0], url=row[1], readers=row[2]) for row in rows],
    )
