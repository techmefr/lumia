from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import FilterMode, UserFeedScore, UserFilterRule
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


def _feed(user: User, external_feed_id: str) -> Feed:
    return Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_feed_id,
        title=f"Feed {external_feed_id}",
        url=f"https://example.com/{external_feed_id}/feed",
    )


def _article(feed: Feed, external_entry_id: str, *, title: str, day: int) -> Article:
    return Article(
        feed_id=feed.id,
        external_entry_id=external_entry_id,
        title=title,
        url=f"https://example.com/{external_entry_id}",
        content="Content",
        published_at=datetime(2026, 8, day, tzinfo=UTC),
    )


async def test_articles_expose_a_neutral_score_when_nothing_is_known(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user, "10")
        session.add(feed)
        await session.flush()
        session.add(_article(feed, "1", title="Article", day=12))
        await session.commit()

    response = await client.get("/articles", headers=headers)

    assert [article["relevance_score"] for article in response.json()] == [50]


async def test_sort_by_relevance_puts_the_liked_feed_first(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        liked = _feed(user, "10")
        other = _feed(user, "20")
        session.add_all([liked, other])
        await session.flush()
        # The relevant one is the older of the two, so recency alone can't produce this order.
        session.add(_article(liked, "1", title="Pertinent", day=1))
        session.add(_article(other, "2", title="Récent", day=12))
        session.add(UserFeedScore(user_id=user.id, feed_id=liked.id, score=3.0))
        await session.commit()

    recent = await client.get("/articles", headers=headers)
    ranked = await client.get("/articles?sort=relevance", headers=headers)

    assert [article["title"] for article in recent.json()] == ["Récent", "Pertinent"]
    assert [article["title"] for article in ranked.json()] == ["Pertinent", "Récent"]
    assert ranked.json()[0]["relevance_score"] > 50


async def test_a_muted_term_hides_the_article_from_the_ranked_list(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = _feed(user, "10")
        session.add(feed)
        await session.flush()
        session.add(_article(feed, "1", title="Le prix du Bitcoin", day=12))
        session.add(_article(feed, "2", title="Un titre neutre", day=11))
        session.add(UserFilterRule(user_id=user.id, term="bitcoin", mode=FilterMode.MUTE))
        await session.commit()

    response = await client.get("/articles?sort=relevance", headers=headers)

    assert [article["title"] for article in response.json()] == ["Un titre neutre"]


async def test_an_unknown_sort_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get("/articles?sort=alphabetical", headers=headers)

    assert response.status_code == 422


async def test_for_duration_creates_a_playlist(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/playlists/for-duration", json={"target_minutes": 25}, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["name"].startswith("25 min · ")
    listed = await client.get("/playlists", headers=headers)
    assert [playlist["id"] for playlist in listed.json()] == [response.json()["id"]]


async def test_for_duration_rejects_an_absurd_budget(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.post(
        "/playlists/for-duration", json={"target_minutes": 4000}, headers=headers
    )

    assert response.status_code == 422


async def test_for_duration_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.post("/playlists/for-duration", json={"target_minutes": 25})

    assert response.status_code == 401
