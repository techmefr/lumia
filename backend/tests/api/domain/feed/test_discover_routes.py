from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Category, Keyword, Lang
from api.domain.feed.discover_catalogue import CATALOGUE
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserCategoryScore, UserKeywordScore
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


async def test_discover_returns_catalogue_entries(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get("/feeds/discover", headers=headers)

    assert response.status_code == 200
    suggestions = response.json()
    assert len(suggestions) == 6
    assert set(suggestions[0]) == {
        "title",
        "url",
        "site_url",
        "description",
        "language",
        "topics",
        "affinity",
    }


async def test_discover_honours_the_limit(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.get("/feeds/discover?limit=2", headers=headers)

    assert len(response.json()) == 2


async def test_discover_excludes_a_feed_already_subscribed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    subscribed = CATALOGUE[0]

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        session.add(
            Feed(
                user_id=user.id,
                source_type=SourceType.MINIFLUX,
                external_feed_id="10",
                title=subscribed.title,
                url=subscribed.url,
            )
        )
        await session.commit()

    response = await client.get(f"/feeds/discover?limit={len(CATALOGUE)}", headers=headers)

    assert subscribed.url not in [suggestion["url"] for suggestion in response.json()]


async def test_discover_ranks_a_source_matching_a_liked_topic_first(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    # A topic that only one catalogue entry carries, so the expectation stays unambiguous.
    target = next(entry for entry in CATALOGUE if "typographie" in entry.topics)

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        keyword = Keyword(term="typographie", lang=Lang.FR)
        session.add(keyword)
        await session.flush()
        session.add(UserKeywordScore(user_id=user.id, keyword_id=keyword.id, score=6.0))
        await session.commit()

    response = await client.get("/feeds/discover", headers=headers)

    assert response.json()[0]["url"] == target.url


async def test_discover_ignores_a_negatively_scored_topic(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        category = Category(name="Science")
        session.add(category)
        await session.flush()
        session.add(UserCategoryScore(user_id=user.id, category_id=category.id, score=-4.0))
        await session.commit()

    response = await client.get(f"/feeds/discover?limit={len(CATALOGUE)}", headers=headers)

    # A dislike must not bury a source: nothing is known, so no affinity is reported at all.
    assert {suggestion["affinity"] for suggestion in response.json()} == {None}


async def test_discover_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    assert (await client.get("/feeds/discover")).status_code == 401
