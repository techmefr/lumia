from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, Folder, SourceType
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


async def _seed() -> dict[str, str]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        folder = Folder(user_id=user.id, name="Tech")
        session.add(folder)
        await session.flush()
        filed = Feed(
            user_id=user.id,
            folder_id=folder.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Filed",
            url="https://example.com/1",
        )
        unfiled = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="2",
            title="Unfiled",
            url="https://example.com/2",
        )
        session.add_all([filed, unfiled])
        await session.flush()
        session.add_all(
            [
                Article(
                    feed_id=filed.id,
                    external_entry_id=f"filed-{index}",
                    title=f"Filed {index}",
                    url=f"https://example.com/filed/{index}",
                    content="Content",
                    published_at=datetime(2026, 8, 12, tzinfo=UTC),
                )
                for index in range(3)
            ]
            + [
                Article(
                    feed_id=unfiled.id,
                    external_entry_id="unfiled-0",
                    title="Unfiled 0",
                    url="https://example.com/unfiled/0",
                    content="Content",
                    published_at=datetime(2026, 8, 11, tzinfo=UTC),
                )
            ]
        )
        await session.commit()
        return {
            "folder_id": str(folder.id),
            "filed_feed_id": str(filed.id),
            "unfiled_feed_id": str(unfiled.id),
        }


async def test_unread_counts_group_by_feed_and_folder(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    body = (await client.get("/feeds/unread-counts", headers=headers)).json()
    assert body["total"] == 4
    assert body["feeds"][ids["filed_feed_id"]] == 3
    assert body["feeds"][ids["unfiled_feed_id"]] == 1
    assert body["folders"] == {ids["folder_id"]: 3}


async def test_unread_counts_drop_after_marking_a_feed_read(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()
    await client.post(
        "/articles/mark-read", json={"feed_id": ids["filed_feed_id"]}, headers=headers
    )

    body = (await client.get("/feeds/unread-counts", headers=headers)).json()
    assert body["total"] == 1
    assert ids["filed_feed_id"] not in body["feeds"]
    assert body["folders"] == {}


async def test_unread_counts_are_empty_without_articles(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    body = (await client.get("/feeds/unread-counts", headers=headers)).json()
    assert body == {"total": 0, "feeds": {}, "folders": {}}
