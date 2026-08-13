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


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed_article() -> str:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        feed = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Feed",
            url="https://example.com/feed",
        )
        session.add(feed)
        await session.flush()
        article = Article(
            feed_id=feed.id,
            external_entry_id="1",
            title="Titre",
            url="https://example.com/a",
            content="Contenu",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        session.add(article)
        await session.commit()
        return str(article.id)


async def test_scroll_progress_starts_at_zero(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    body = (await client.get(f"/articles/{article_id}", headers=headers)).json()
    assert body["scroll_progress"] == 0.0


async def test_scroll_progress_is_persisted(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    await client.post(
        f"/articles/{article_id}/feedback", json={"scroll_progress": 0.42}, headers=headers
    )

    body = (await client.get(f"/articles/{article_id}", headers=headers)).json()
    assert body["scroll_progress"] == pytest.approx(0.42)


async def test_scroll_progress_never_goes_backwards(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    await client.post(
        f"/articles/{article_id}/feedback", json={"scroll_progress": 0.8}, headers=headers
    )
    await client.post(
        f"/articles/{article_id}/feedback", json={"scroll_progress": 0.1}, headers=headers
    )

    body = (await client.get(f"/articles/{article_id}", headers=headers)).json()
    assert body["scroll_progress"] == pytest.approx(0.8)


async def test_scroll_progress_appears_in_the_list(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()
    await client.post(
        f"/articles/{article_id}/feedback", json={"scroll_progress": 0.5}, headers=headers
    )

    listed = (await client.get("/articles", headers=headers)).json()
    assert listed[0]["scroll_progress"] == pytest.approx(0.5)


async def test_scroll_progress_out_of_range_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    response = await client.post(
        f"/articles/{article_id}/feedback", json={"scroll_progress": 1.5}, headers=headers
    )
    assert response.status_code == 422


async def test_setting_progress_does_not_mark_the_article_read(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    article_id = await _seed_article()

    await client.post(
        f"/articles/{article_id}/feedback", json={"scroll_progress": 0.9}, headers=headers
    )

    body = (await client.get(f"/articles/{article_id}", headers=headers)).json()
    assert body["read"] is False
