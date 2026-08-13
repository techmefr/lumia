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


async def test_saved_only_returns_articles_voted_save(client: httpx.AsyncClient) -> None:
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
        saved = Article(
            feed_id=feed.id,
            external_entry_id="1",
            title="Saved",
            url="https://example.com/1",
            content="Content",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        liked = Article(
            feed_id=feed.id,
            external_entry_id="2",
            title="Liked",
            url="https://example.com/2",
            content="Content",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add_all([saved, liked])
        await session.flush()
        session.add(UserArticleFeedback(user_id=user.id, article_id=saved.id, vote=Vote.SAVE))
        session.add(UserArticleFeedback(user_id=user.id, article_id=liked.id, vote=Vote.LIKE))
        await session.commit()

    response = await client.get("/articles/saved", headers=headers)
    assert response.status_code == 200
    titles = [article["title"] for article in response.json()]
    assert titles == ["Saved"]


async def test_saved_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/articles/saved")
    assert response.status_code == 401
