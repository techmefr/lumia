from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Author, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback, Vote
from api.domain.recommendation.statistics_service import POPULARITY_MIN_READERS
from api.domain.user.models import User
from api.main import app
from config.database import get_engine

ADMIN_PAYLOAD = {
    "email": "admin@example.com",
    "username": "admin",
    "password": "correct-horse-battery-staple",
}


@pytest.fixture
async def client(db_schema: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _sessions() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


def _feed(user_id: UUID, title: str, source_type: SourceType = SourceType.MINIFLUX) -> Feed:
    return Feed(
        user_id=user_id,
        source_type=source_type,
        external_feed_id=title,
        title=title,
        url=f"https://example.com/{title}",
    )


def _article(
    feed: Feed,
    slug: str,
    *,
    content: str = "word " * 400,
    author: Author | None = None,
    published_at: datetime | None = None,
) -> Article:
    return Article(
        feed_id=feed.id,
        author_id=author.id if author else None,
        external_entry_id=f"{feed.title}-{slug}",
        title=slug,
        url=f"https://example.com/{slug}",
        content=content,
        published_at=published_at or datetime.now(UTC) - timedelta(days=1),
    )


def _read(user_id: UUID, article: Article, read_at: datetime) -> UserArticleFeedback:
    return UserArticleFeedback(user_id=user_id, article_id=article.id, read=True, read_at=read_at)


async def test_statistics_require_authentication(client: httpx.AsyncClient) -> None:
    assert (await client.get("/statistics/reading")).status_code == 401
    assert (await client.get("/statistics/popular")).status_code == 401


async def test_reading_statistics_are_empty_for_a_new_account(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get("/statistics/reading?days=7", headers=headers)

    body = response.json()
    assert response.status_code == 200
    assert body["articles_read"] == 0
    assert body["reading_minutes"] == 0
    assert len(body["daily"]) == 7
    assert body["feed_engagement"] == []
    assert body["totals"] == {"saved": 0, "favorites": 0, "liked": 0, "disliked": 0}


async def test_days_outside_the_allowed_range_are_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    assert (await client.get("/statistics/reading?days=0", headers=headers)).status_code == 422
    assert (await client.get("/statistics/reading?days=366", headers=headers)).status_code == 422
    assert (await client.get("/statistics/popular?days=91", headers=headers)).status_code == 422


async def test_reading_volume_is_summed_per_day_with_estimated_minutes(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    now = datetime.now(UTC)
    async with _sessions()() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user.id, "Feed")
        session.add(feed)
        await session.flush()
        long_article = _article(feed, "long", content="<p>" + "word " * 400 + "</p>")
        short_article = _article(feed, "short", content="two words")
        old_article = _article(feed, "old")
        session.add_all([long_article, short_article, old_article])
        await session.flush()
        session.add_all(
            [
                _read(user.id, long_article, now),
                _read(user.id, short_article, now),
                _read(user.id, old_article, now - timedelta(days=40)),
            ]
        )
        await session.commit()

    body = (await client.get("/statistics/reading?days=7", headers=headers)).json()

    assert body["articles_read"] == 2
    assert body["reading_minutes"] == 3
    today = body["daily"][-1]
    assert (today["articles_read"], today["reading_minutes"]) == (2, 3)
    assert body["daily"][0]["articles_read"] == 0


async def test_rankings_count_reads_by_feed_author_and_keyword(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    now = datetime.now(UTC)
    async with _sessions()() as session:
        user = (await session.scalars(select(User))).one()
        favourite_feed = _feed(user.id, "Favourite")
        other_feed = _feed(user.id, "Other")
        author = Author(name="Ada")
        keyword = Keyword(term="python", lang=Lang.EN)
        session.add_all([favourite_feed, other_feed, author, keyword])
        await session.flush()
        articles = [
            _article(favourite_feed, "a", author=author),
            _article(favourite_feed, "b", author=author),
            _article(other_feed, "c"),
        ]
        session.add_all(articles)
        await session.flush()
        session.add_all(
            ArticleKeyword(article_id=a.id, keyword_id=keyword.id, weight=1) for a in articles
        )
        session.add_all(_read(user.id, a, now) for a in articles)
        await session.commit()

    body = (await client.get("/statistics/reading", headers=headers)).json()

    assert [(f["name"], f["articles_read"]) for f in body["top_feeds"]] == [
        ("Favourite", 2),
        ("Other", 1),
    ]
    assert [(a["name"], a["articles_read"]) for a in body["top_authors"]] == [("Ada", 2)]
    assert body["top_keywords"] == [{"term": "python", "articles_read": 3}]


async def test_feed_engagement_ranks_the_most_ignored_feed_first(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    now = datetime.now(UTC)
    async with _sessions()() as session:
        user = (await session.scalars(select(User))).one()
        noisy = _feed(user.id, "Noisy")
        loved = _feed(user.id, "Loved")
        saved_pages = _feed(user.id, "Saved", SourceType.MANUAL)
        session.add_all([noisy, loved, saved_pages])
        await session.flush()
        noisy_articles = [_article(noisy, f"n{i}") for i in range(4)]
        loved_articles = [_article(loved, f"l{i}") for i in range(2)]
        saved_article = _article(saved_pages, "s")
        session.add_all([*noisy_articles, *loved_articles, saved_article])
        await session.flush()
        session.add_all(
            [
                _read(user.id, noisy_articles[0], now),
                _read(user.id, loved_articles[0], now),
                _read(user.id, loved_articles[1], now),
            ]
        )
        await session.commit()

    body = (await client.get("/statistics/reading", headers=headers)).json()

    assert body["feed_engagement"] == [
        {
            "feed_id": str(noisy.id),
            "title": "Noisy",
            "received": 4,
            "read": 1,
            "ignored": 3,
            "read_ratio": 0.25,
        },
        {
            "feed_id": str(loved.id),
            "title": "Loved",
            "received": 2,
            "read": 2,
            "ignored": 0,
            "read_ratio": 1.0,
        },
    ]


async def test_totals_count_saved_favourites_and_votes(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    async with _sessions()() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user.id, "Feed")
        session.add(feed)
        await session.flush()
        articles = [_article(feed, f"t{i}") for i in range(3)]
        session.add_all(articles)
        await session.flush()
        session.add_all(
            [
                UserArticleFeedback(
                    user_id=user.id, article_id=articles[0].id, saved=True, sentiment=Vote.LIKE
                ),
                UserArticleFeedback(
                    user_id=user.id,
                    article_id=articles[1].id,
                    favorite=True,
                    sentiment=Vote.DISLIKE,
                ),
                UserArticleFeedback(user_id=user.id, article_id=articles[2].id, favorite=True),
            ]
        )
        await session.commit()

    body = (await client.get("/statistics/reading", headers=headers)).json()

    assert body["totals"] == {"saved": 1, "favorites": 2, "liked": 1, "disliked": 1}


async def test_statistics_never_include_another_readers_activity(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    async with _sessions()() as session:
        admin = (await session.scalars(select(User))).one()
        other = User(instance_id=admin.instance_id, email="other@example.com", username="other")
        session.add(other)
        await session.flush()
        feed = _feed(other.id, "Theirs")
        session.add(feed)
        await session.flush()
        article = _article(feed, "private")
        session.add(article)
        await session.flush()
        session.add(_read(other.id, article, datetime.now(UTC)))
        await session.commit()

    body = (await client.get("/statistics/reading", headers=headers)).json()

    assert body["articles_read"] == 0
    assert body["top_feeds"] == []
    assert body["feed_engagement"] == []


async def test_days_follow_the_readers_timezone(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    now = datetime.now(UTC)
    async with _sessions()() as session:
        user = (await session.scalars(select(User))).one()
        user.digest_timezone = "Pacific/Auckland"
        feed = _feed(user.id, "Feed")
        session.add(feed)
        await session.flush()
        article = _article(feed, "a")
        session.add(article)
        await session.flush()
        session.add(_read(user.id, article, now))
        await session.commit()

    body = (await client.get("/statistics/reading?days=3", headers=headers)).json()

    assert body["articles_read"] == 1
    assert body["daily"][-1]["articles_read"] == 1


async def _seed_readers(
    readers: int, *, slug: str = "shared", read_at: datetime | None = None
) -> None:
    async with _sessions()() as session:
        admin = (await session.scalars(select(User))).one()
        for index in range(readers):
            user = admin
            if index > 0:
                user = User(
                    instance_id=admin.instance_id,
                    email=f"reader{index}@example.com",
                    username=f"reader{index}",
                )
                session.add(user)
                await session.flush()
            feed = _feed(user.id, f"Feed{index}")
            session.add(feed)
            await session.flush()
            article = _article(feed, slug)
            session.add(article)
            await session.flush()
            session.add(_read(user.id, article, read_at or datetime.now(UTC)))
        await session.commit()


async def test_popularity_lists_articles_read_by_enough_readers(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seed_readers(POPULARITY_MIN_READERS)

    body = (await client.get("/statistics/popular", headers=headers)).json()

    assert body["min_readers"] == POPULARITY_MIN_READERS
    assert body["articles"] == [
        {
            "title": "shared",
            "url": "https://example.com/shared",
            "readers": POPULARITY_MIN_READERS,
        }
    ]


async def test_popularity_hides_articles_under_the_reader_threshold(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seed_readers(POPULARITY_MIN_READERS - 1)

    body = (await client.get("/statistics/popular", headers=headers)).json()

    assert body["articles"] == []


async def test_popularity_ignores_reads_outside_the_period(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_readers(POPULARITY_MIN_READERS, read_at=datetime.now(UTC) - timedelta(days=30))

    body = (await client.get("/statistics/popular?days=7", headers=headers)).json()

    assert body["articles"] == []


async def test_popularity_payload_carries_no_reader_identity(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_readers(POPULARITY_MIN_READERS)

    raw = (await client.get("/statistics/popular", headers=headers)).text

    assert "reader1" not in raw
    assert "admin" not in raw
    assert "example.com/Feed" not in raw
