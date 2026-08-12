from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
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


async def _headers_and_article_id(client: httpx.AsyncClient) -> tuple[dict[str, str], str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    body = response.json()
    access_token = body["access_token"]

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
        article = Article(
            feed_id=feed.id,
            external_entry_id="1",
            title="Title",
            url="https://example.com/a",
            content="Content",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        article_id = str(article.id)

    return {"Authorization": f"Bearer {access_token}"}, article_id


async def test_feedback_on_a_known_article_returns_204(client: httpx.AsyncClient) -> None:
    headers, article_id = await _headers_and_article_id(client)
    response = await client.post(
        f"/articles/{article_id}/feedback", headers=headers, json={"vote": "like"}
    )
    assert response.status_code == 204


async def test_feedback_on_an_unknown_article_returns_404(client: httpx.AsyncClient) -> None:
    headers, _ = await _headers_and_article_id(client)
    response = await client.post(
        "/articles/00000000-0000-0000-0000-000000000000/feedback",
        headers=headers,
        json={"vote": "like"},
    )
    assert response.status_code == 404


async def test_feedback_without_a_token_returns_401(client: httpx.AsyncClient) -> None:
    _, article_id = await _headers_and_article_id(client)
    response = await client.post(f"/articles/{article_id}/feedback", json={"vote": "like"})
    assert response.status_code == 401
