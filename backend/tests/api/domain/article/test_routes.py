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
from api.technical.auth.jwt import create_access_token
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


async def _seed_article(*, title: str = "Title", external_entry_id: str = "1") -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).first()
        assert user is not None
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
            external_entry_id=external_entry_id,
            title=title,
            url="https://example.com/a",
            content="Content",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


async def test_list_articles_returns_the_current_users_articles(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seed_article()

    response = await client.get("/articles", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Title"


async def test_list_articles_excludes_articles_of_other_users(
    client: httpx.AsyncClient,
) -> None:
    await _headers(client)
    await _seed_article()

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        other_user = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other_user)
        await session.commit()
        other_user_id = other_user.id

    other_headers = {"Authorization": f"Bearer {create_access_token(other_user_id)}"}
    response = await client.get("/articles", headers=other_headers)
    assert response.json() == []


async def test_get_article_returns_its_detail(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    response = await client.get(f"/articles/{article_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Content"


async def test_get_article_of_another_user_returns_404(client: httpx.AsyncClient) -> None:
    await _headers(client)
    article_id = await _seed_article()

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).first()
        assert user is not None
        other_user = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other_user)
        await session.commit()
        other_user_id = other_user.id

    other_headers = {"Authorization": f"Bearer {create_access_token(other_user_id)}"}
    response = await client.get(f"/articles/{article_id}", headers=other_headers)
    assert response.status_code == 404
