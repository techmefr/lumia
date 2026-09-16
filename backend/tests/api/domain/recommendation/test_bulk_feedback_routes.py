from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.recommendation.models import UserArticleFeedback
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
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _seed() -> dict[str, str]:
    """Two feeds, one of them in a folder, one article each."""
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
        in_folder = Article(
            feed_id=first.id,
            external_entry_id="a",
            title="In folder",
            url="https://example.com/a",
            content="Content",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        outside = Article(
            feed_id=second.id,
            external_entry_id="b",
            title="Outside folder",
            url="https://example.com/b",
            content="Content",
            published_at=datetime(2026, 8, 11, tzinfo=UTC),
        )
        session.add_all([in_folder, outside])
        await session.commit()
        return {
            "folder_id": str(folder.id),
            "feed_id": str(first.id),
            "in_folder": str(in_folder.id),
            "outside": str(outside.id),
        }


async def _feedback_rows() -> list[UserArticleFeedback]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as session:
        return list(await session.scalars(select(UserArticleFeedback)))


async def test_favouriting_a_selection_only_touches_the_chosen_articles(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.post(
        "/articles/bulk-feedback",
        json={"article_ids": [ids["in_folder"]], "axis": "favorite", "value": True},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"updated": 1, "changed_article_ids": [ids["in_folder"]]}
    favorites = (await client.get("/articles/favorites", headers=headers)).json()
    assert [article["title"] for article in favorites] == ["In folder"]


async def test_an_axis_leaves_the_other_axes_alone(client: httpx.AsyncClient) -> None:
    """Sentiment, saved, favourite and read are independent: saving says nothing about reading."""
    headers = await _headers(client)
    ids = await _seed()

    await client.post(
        "/articles/bulk-feedback",
        json={"article_ids": [ids["in_folder"]], "axis": "saved", "value": True},
        headers=headers,
    )

    row = (await _feedback_rows())[0]
    assert (row.saved, row.favorite, row.read, row.sentiment) == (True, False, False, None)


async def test_the_reported_changes_exclude_articles_that_already_held_the_value(
    client: httpx.AsyncClient,
) -> None:
    """An undo reverts the reported ids, so an article already saved must not appear among them."""
    headers = await _headers(client)
    ids = await _seed()
    await client.post(
        "/articles/bulk-feedback",
        json={"article_ids": [ids["in_folder"]], "axis": "saved", "value": True},
        headers=headers,
    )

    response = await client.post(
        "/articles/bulk-feedback",
        json={
            "article_ids": [ids["in_folder"], ids["outside"]],
            "axis": "saved",
            "value": True,
        },
        headers=headers,
    )

    assert response.json() == {"updated": 2, "changed_article_ids": [ids["outside"]]}


async def test_a_feed_scope_reaches_every_article_of_that_feed_only(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.post(
        "/articles/bulk-feedback",
        json={"feed_id": ids["feed_id"], "axis": "read", "value": True},
        headers=headers,
    )

    assert response.json()["changed_article_ids"] == [ids["in_folder"]]
    listed = (await client.get("/articles", headers=headers)).json()
    assert {article["title"]: article["read"] for article in listed} == {
        "In folder": True,
        "Outside folder": False,
    }


async def test_a_folder_scope_reaches_every_feed_of_that_folder(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.post(
        "/articles/bulk-feedback",
        json={"folder_id": ids["folder_id"], "axis": "read", "value": True},
        headers=headers,
    )

    assert response.json()["changed_article_ids"] == [ids["in_folder"]]


async def test_all_reaches_the_whole_library(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _seed()

    response = await client.post(
        "/articles/bulk-feedback",
        json={"all": True, "axis": "saved", "value": True},
        headers=headers,
    )

    assert response.json()["updated"] == 2


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="no scope at all"),
        pytest.param({"all": False}, id="all passed but false"),
        pytest.param({"feed_id": "00000000-0000-0000-0000-000000000001", "all": True}, id="two"),
        pytest.param(
            {
                "feed_id": "00000000-0000-0000-0000-000000000001",
                "folder_id": "00000000-0000-0000-0000-000000000002",
            },
            id="two ids",
        ),
        pytest.param({"article_ids": [], "all": True}, id="a list and all"),
    ],
)
async def test_anything_but_exactly_one_scope_is_rejected(
    client: httpx.AsyncClient, body: dict[str, Any]
) -> None:
    """The same contract as mark-read: a forgotten filter must not reach the whole library."""
    headers = await _headers(client)

    response = await client.post(
        "/articles/bulk-feedback", json={**body, "axis": "read", "value": True}, headers=headers
    )

    assert response.status_code == 422


async def test_an_unknown_axis_is_rejected(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    response = await client.post(
        "/articles/bulk-feedback",
        json={"article_ids": [ids["in_folder"]], "axis": "sentiment", "value": True},
        headers=headers,
    )

    assert response.status_code == 422


async def test_articles_of_another_user_are_out_of_reach(client: httpx.AsyncClient) -> None:
    await _headers(client)
    ids = await _seed()
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

    response = await client.post(
        "/articles/bulk-feedback",
        json={"article_ids": [ids["in_folder"]], "axis": "read", "value": True},
        headers={"Authorization": f"Bearer {create_access_token(other_id)}"},
    )

    assert response.json() == {"updated": 0, "changed_article_ids": []}
    assert await _feedback_rows() == []


async def test_a_write_failing_halfway_leaves_the_whole_selection_untouched(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The batch lands whole or not at all: a half-applied selection is one the reader cannot see,
    and therefore cannot fix."""
    headers = await _headers(client)
    ids = await _seed()

    async def fail(_self: AsyncSession) -> None:
        raise OperationalError("bulk", None, Exception("connection lost"))

    monkeypatch.setattr(AsyncSession, "commit", fail)

    response = await client.post(
        "/articles/bulk-feedback",
        json={
            "article_ids": [ids["in_folder"], ids["outside"]],
            "axis": "read",
            "value": True,
        },
        headers=headers,
    )

    assert response.status_code == 500
    monkeypatch.undo()
    assert await _feedback_rows() == []
    listed = (await client.get("/articles", headers=headers)).json()
    assert all(article["read"] is False for article in listed)
