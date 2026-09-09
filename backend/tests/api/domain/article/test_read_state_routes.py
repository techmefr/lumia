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


async def _seed_two_feeds_in_a_folder() -> dict[str, str]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        folder = Folder(user_id=user.id, name="Tech")
        session.add(folder)
        await session.flush()
        first = Feed(
            user_id=user.id,
            folder_id=folder.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="First",
            url="https://example.com/1",
        )
        second = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="2",
            title="Second",
            url="https://example.com/2",
        )
        session.add_all([first, second])
        await session.flush()
        session.add_all(
            [
                Article(
                    feed_id=first.id,
                    external_entry_id="a",
                    title="In folder",
                    url="https://example.com/a",
                    content="Content",
                    published_at=datetime(2026, 8, 12, tzinfo=UTC),
                ),
                Article(
                    feed_id=second.id,
                    external_entry_id="b",
                    title="Outside folder",
                    url="https://example.com/b",
                    content="Content",
                    published_at=datetime(2026, 8, 11, tzinfo=UTC),
                ),
            ]
        )
        await session.commit()
        return {"folder_id": str(folder.id), "feed_id": str(first.id)}


async def test_articles_are_unread_by_default(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_two_feeds_in_a_folder()

    response = await client.get("/articles", headers=headers)
    assert [article["read"] for article in response.json()] == [False, False]


async def test_feedback_read_flag_is_reflected_in_the_list(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_two_feeds_in_a_folder()
    article_id = (await client.get("/articles", headers=headers)).json()[0]["id"]

    await client.post(f"/articles/{article_id}/feedback", json={"read": True}, headers=headers)

    response = await client.get("/articles", headers=headers)
    by_id = {article["id"]: article["read"] for article in response.json()}
    assert by_id[article_id] is True


async def test_unread_only_excludes_read_articles(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_two_feeds_in_a_folder()
    article_id = (await client.get("/articles", headers=headers)).json()[0]["id"]
    await client.post(f"/articles/{article_id}/feedback", json={"read": True}, headers=headers)

    response = await client.get("/articles?unread_only=true", headers=headers)
    assert [article["title"] for article in response.json()] == ["Outside folder"]
    assert article_id not in [article["id"] for article in response.json()]


async def test_mark_read_by_feed_only_marks_that_feed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed_two_feeds_in_a_folder()

    response = await client.post(
        "/articles/mark-read", json={"feed_id": ids["feed_id"]}, headers=headers
    )
    assert response.status_code == 200
    assert response.json() == {"updated": 1}

    listed = (await client.get("/articles", headers=headers)).json()
    assert {article["title"]: article["read"] for article in listed} == {
        "In folder": True,
        "Outside folder": False,
    }


async def test_mark_read_by_folder_marks_every_feed_of_the_folder(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    ids = await _seed_two_feeds_in_a_folder()

    response = await client.post(
        "/articles/mark-read", json={"folder_id": ids["folder_id"]}, headers=headers
    )
    assert response.json() == {"updated": 1}

    listed = (await client.get("/articles", headers=headers)).json()
    assert {article["title"]: article["read"] for article in listed} == {
        "In folder": True,
        "Outside folder": False,
    }


async def test_mark_read_can_unmark(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed_two_feeds_in_a_folder()
    await client.post("/articles/mark-read", json={"feed_id": ids["feed_id"]}, headers=headers)

    await client.post(
        "/articles/mark-read",
        json={"feed_id": ids["feed_id"], "read": False},
        headers=headers,
    )

    listed = (await client.get("/articles", headers=headers)).json()
    assert all(article["read"] is False for article in listed)


async def test_mark_read_with_all_marks_every_feed(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed_two_feeds_in_a_folder()

    response = await client.post("/articles/mark-read", json={"all": True}, headers=headers)
    assert response.json() == {"updated": 2}

    listed = (await client.get("/articles", headers=headers)).json()
    assert all(article["read"] is True for article in listed)


async def test_mark_read_with_all_false_and_no_other_scope_is_rejected(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    response = await client.post("/articles/mark-read", json={"all": False}, headers=headers)
    assert response.status_code == 422


async def test_mark_read_without_a_scope_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    response = await client.post("/articles/mark-read", json={}, headers=headers)
    assert response.status_code == 422


async def test_mark_read_with_two_scopes_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed_two_feeds_in_a_folder()
    response = await client.post(
        "/articles/mark-read",
        json={"feed_id": ids["feed_id"], "folder_id": ids["folder_id"]},
        headers=headers,
    )
    assert response.status_code == 422


async def test_mark_read_ignores_articles_of_another_user(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed_two_feeds_in_a_folder()

    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        user = (await session.scalars(select(User))).one()
        other = User(
            instance_id=user.instance_id,
            email="other@example.com",
            username="other",
            password_hash=None,
        )
        session.add(other)
        await session.commit()
        other_id = other.id

    other_headers = {"Authorization": f"Bearer {create_access_token(other_id)}"}
    response = await client.post(
        "/articles/mark-read", json={"feed_id": ids["feed_id"]}, headers=other_headers
    )
    assert response.json() == {"updated": 0}

    listed = (await client.get("/articles", headers=headers)).json()
    assert all(article["read"] is False for article in listed)
