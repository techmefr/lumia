from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.recommendation.models import FilterMode, UserArticleFeedback, UserFilterRule
from api.domain.saved_search.models import AlertNotification, SavedSearch
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


def _session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def _seed() -> dict[str, UUID]:
    """Two feeds, one in a folder; three articles, two of them about rust."""
    async with _session_factory()() as session:
        user = (await session.scalars(select(User))).one()
        folder = Folder(user_id=user.id, name="Dev")
        session.add(folder)
        await session.flush()
        blog = Feed(
            user_id=user.id,
            folder_id=folder.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Blog",
            url="https://example.com/blog",
        )
        news = Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="2",
            title="News",
            url="https://example.com/news",
        )
        session.add_all([blog, news])
        await session.flush()
        articles = [
            Article(
                feed_id=blog.id,
                external_entry_id="a",
                title="Rust ships a release",
                url="https://example.com/a",
                content="Contenu",
                published_at=datetime(2026, 8, 12, tzinfo=UTC),
            ),
            Article(
                feed_id=news.id,
                external_entry_id="b",
                title="More rust news",
                url="https://example.com/b",
                content="Contenu",
                published_at=datetime(2026, 8, 11, tzinfo=UTC),
            ),
            Article(
                feed_id=news.id,
                external_entry_id="c",
                title="Cooking",
                url="https://example.com/c",
                content="Contenu",
                published_at=datetime(2026, 8, 10, tzinfo=UTC),
            ),
        ]
        session.add_all(articles)
        await session.commit()
        return {
            "user": user.id,
            "folder": folder.id,
            "blog": blog.id,
            "news": news.id,
            "rust_blog": articles[0].id,
            "rust_news": articles[1].id,
        }


async def _create(
    client: httpx.AsyncClient, headers: dict[str, str], **fields: object
) -> httpx.Response:
    payload = {"name": "Rust", "query": "rust", **fields}
    return await client.post("/saved-searches", json=payload, headers=headers)


async def _notify(ids: dict[str, UUID], search_id: str, *article_keys: str) -> list[UUID]:
    async with _session_factory()() as session:
        rows = [
            AlertNotification(
                user_id=ids["user"], saved_search_id=UUID(search_id), article_id=ids[key]
            )
            for key in article_keys
        ]
        session.add_all(rows)
        await session.commit()
        return [row.id for row in rows]


async def test_a_saved_search_carries_the_count_of_its_unread_articles(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    await _seed()

    created = await _create(client, headers)

    assert created.status_code == 201
    assert created.json()["unread_count"] == 2
    listed = await client.get("/saved-searches", headers=headers)
    assert [(s["name"], s["unread_count"]) for s in listed.json()] == [("Rust", 2)]


async def test_reading_an_article_lowers_the_count(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()
    await _create(client, headers)
    async with _session_factory()() as session:
        session.add(
            UserArticleFeedback(user_id=ids["user"], article_id=ids["rust_blog"], read=True)
        )
        await session.commit()

    listed = await client.get("/saved-searches", headers=headers)

    assert listed.json()[0]["unread_count"] == 1


async def test_the_scope_narrows_the_count(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()

    by_feed = await _create(client, headers, name="In news", feed_id=str(ids["news"]))
    by_folder = await _create(client, headers, name="In dev", folder_id=str(ids["folder"]))

    assert by_feed.json()["unread_count"] == 1
    assert by_folder.json()["unread_count"] == 1


async def test_muted_terms_do_not_count(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()
    async with _session_factory()() as session:
        session.add(UserFilterRule(user_id=ids["user"], term="more", mode=FilterMode.MUTE))
        await session.commit()

    created = await _create(client, headers)

    assert created.json()["unread_count"] == 1


async def test_a_name_cannot_be_used_twice(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    assert (await _create(client, headers)).status_code == 201
    assert (await _create(client, headers)).status_code == 409


async def test_a_scope_that_is_not_the_reader_own_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    unknown_feed = await _create(client, headers, feed_id=str(uuid4()))
    unknown_folder = await _create(client, headers, name="Other", folder_id=str(uuid4()))

    assert unknown_feed.status_code == 404
    assert unknown_folder.status_code == 404


async def test_a_too_short_query_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await _create(client, headers, query="a")

    assert response.status_code == 422


async def test_a_search_can_be_promoted_to_an_alert_and_renamed(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    created = (await _create(client, headers)).json()

    patched = await client.patch(
        f"/saved-searches/{created['id']}",
        json={"alert": True, "name": "Rust news"},
        headers=headers,
    )

    assert patched.status_code == 200
    assert (patched.json()["alert"], patched.json()["name"]) == (True, "Rust news")


async def test_renaming_onto_an_existing_name_is_refused(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _create(client, headers, name="First")
    second = (await _create(client, headers, name="Second")).json()

    response = await client.patch(
        f"/saved-searches/{second['id']}", json={"name": "First"}, headers=headers
    )

    assert response.status_code == 409


async def test_patching_an_unknown_search_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.patch(
        f"/saved-searches/{uuid4()}", json={"alert": True}, headers=headers
    )

    assert response.status_code == 404


async def test_deleting_a_search_takes_its_notifications(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()
    created = (await _create(client, headers, alert=True)).json()
    await _notify(ids, created["id"], "rust_blog")

    deleted = await client.delete(f"/saved-searches/{created['id']}", headers=headers)

    assert deleted.status_code == 204
    async with _session_factory()() as session:
        assert await session.scalar(select(func.count()).select_from(SavedSearch)) == 0
        assert await session.scalar(select(func.count()).select_from(AlertNotification)) == 0


async def test_deleting_an_unknown_search_returns_404(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)

    response = await client.delete(f"/saved-searches/{uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_deleting_a_feed_drops_the_searches_pinned_to_it(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()
    await _create(client, headers, name="Pinned", feed_id=str(ids["blog"]))
    await _create(client, headers, name="Global")
    async with _session_factory()() as session:
        await session.execute(delete(Article).where(Article.feed_id == ids["blog"]))
        await session.commit()

    response = await client.delete(f"/feeds/{ids['blog']}", headers=headers)

    assert response.status_code == 204
    listed = await client.get("/saved-searches", headers=headers)
    assert [search["name"] for search in listed.json()] == ["Global"]


async def test_deleting_a_folder_drops_the_searches_pinned_to_it(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    ids = await _seed()
    await _create(client, headers, name="Pinned", folder_id=str(ids["folder"]))

    response = await client.delete(f"/folders/{ids['folder']}", headers=headers)

    assert response.status_code == 204
    assert (await client.get("/saved-searches", headers=headers)).json() == []


async def test_notifications_list_newest_first_with_the_unread_total(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    ids = await _seed()
    created = (await _create(client, headers, alert=True)).json()
    older, newer = await _notify(ids, created["id"], "rust_blog", "rust_news")
    async with _session_factory()() as session:
        for notification_id, day, read in ((older, 12, False), (newer, 13, True)):
            notification = await session.get(AlertNotification, notification_id)
            assert notification is not None
            notification.created_at = datetime(2026, 8, day, tzinfo=UTC)
            notification.read = read
        await session.commit()

    response = await client.get("/notifications", headers=headers)

    body = response.json()
    assert body["unread_count"] == 1
    assert [(n["article_title"], n["saved_search_name"], n["read"]) for n in body["items"]] == [
        ("More rust news", "Rust", True),
        ("Rust ships a release", "Rust", False),
    ]


async def test_notifications_are_paginated(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    ids = await _seed()
    created = (await _create(client, headers, alert=True)).json()
    await _notify(ids, created["id"], "rust_blog", "rust_news")

    page = await client.get("/notifications?limit=1&offset=1", headers=headers)

    assert len(page.json()["items"]) == 1
    assert page.json()["unread_count"] == 2


async def _two_notifications(client: httpx.AsyncClient, headers: dict[str, str]) -> list[UUID]:
    ids = await _seed()
    created = (await _create(client, headers, alert=True)).json()
    return await _notify(ids, created["id"], "rust_blog", "rust_news")


async def test_marking_given_notifications_read_leaves_the_others(
    client: httpx.AsyncClient,
) -> None:
    headers = await _headers(client)
    notification_ids = await _two_notifications(client, headers)

    response = await client.post(
        "/notifications/mark-read", json={"ids": [str(notification_ids[0])]}, headers=headers
    )

    assert response.status_code == 204
    assert (await client.get("/notifications", headers=headers)).json()["unread_count"] == 1


async def test_marking_without_ids_reads_everything(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    await _two_notifications(client, headers)

    await client.post("/notifications/mark-read", json={}, headers=headers)

    assert (await client.get("/notifications", headers=headers)).json()["unread_count"] == 0


async def test_another_reader_sees_and_touches_nothing(client: httpx.AsyncClient) -> None:
    headers = await _headers(client)
    notification_ids = await _two_notifications(client, headers)
    created = (await client.get("/saved-searches", headers=headers)).json()[0]
    async with _session_factory()() as session:
        admin = (await session.scalars(select(User))).one()
        other = User(instance_id=admin.instance_id, email="o@example.com", username="o")
        session.add(other)
        await session.commit()
    other_headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}

    assert (await client.get("/saved-searches", headers=other_headers)).json() == []
    assert (await client.get("/notifications", headers=other_headers)).json()["items"] == []
    deleted = await client.delete(f"/saved-searches/{created['id']}", headers=other_headers)
    assert deleted.status_code == 404
    await client.post(
        "/notifications/mark-read", json={"ids": [str(notification_ids[0])]}, headers=other_headers
    )
    assert (await client.get("/notifications", headers=headers)).json()["unread_count"] == 2


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/saved-searches"),
        ("POST", "/saved-searches"),
        ("PATCH", f"/saved-searches/{uuid4()}"),
        ("DELETE", f"/saved-searches/{uuid4()}"),
        ("GET", "/notifications"),
        ("POST", "/notifications/mark-read"),
    ],
)
async def test_every_route_requires_a_token(
    client: httpx.AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path)

    assert response.status_code == 401
