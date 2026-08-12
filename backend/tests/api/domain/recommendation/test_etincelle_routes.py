from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback, Vote
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


async def test_etincelle_excludes_a_voted_article(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="10",
            title="Feed",
            url="https://example.com/feed",
        )
        session.add(feed)
        await session.flush()
        voted = Article(
            feed_id=feed.id,
            external_entry_id="1",
            title="Voted",
            url="https://example.com/1",
            content="Content",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        unvoted = Article(
            feed_id=feed.id,
            external_entry_id="2",
            title="Unvoted",
            url="https://example.com/2",
            content="Content",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add_all([voted, unvoted])
        await session.flush()
        session.add(UserArticleFeedback(user_id=user.id, article_id=voted.id, vote=Vote.LIKE))
        await session.commit()

    response = await client.get("/articles/etincelle", headers=headers)
    assert response.status_code == 200
    titles = [article["title"] for article in response.json()]
    assert titles == ["Unvoted"]


async def test_etincelle_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/articles/etincelle")
    assert response.status_code == 401
