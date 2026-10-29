from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.user.models import Instance, User
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


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/onboarding/admin", json=ADMIN_PAYLOAD)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _other_user(session: AsyncSession) -> User:
    instance = (await session.scalars(select(Instance))).one()
    user = User(instance_id=instance.id, email="other@example.com", username="other")
    session.add(user)
    await session.commit()
    return user


async def test_the_server_decides_the_source_and_the_external_id(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    headers = await _admin_headers(client)

    response = await client.post(
        "/feeds",
        headers=headers,
        json={
            "source_type": "manual",
            "external_feed_id": "1",
            "title": "Mine",
            "url": "https://example.com/rss",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "miniflux"
    assert body["external_feed_id"] != "1"
    assert body["external_feed_id"].startswith("-")


async def test_two_feeds_created_by_hand_never_share_an_external_id(
    client: httpx.AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    payload = {"title": "Mine", "url": "https://example.com/rss"}

    first = await client.post("/feeds", headers=headers, json=payload)
    second = await client.post("/feeds", headers=headers, json=payload)

    assert first.json()["external_feed_id"] != second.json()["external_feed_id"]


async def test_a_feed_cannot_be_filed_in_the_folder_of_another_reader(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    headers = await _admin_headers(client)
    other = await _other_user(session)
    foreign_folder = Folder(user_id=other.id, name="Theirs")
    session.add(foreign_folder)
    await session.commit()

    response = await client.post(
        "/feeds",
        headers=headers,
        json={
            "title": "Mine",
            "url": "https://example.com/rss",
            "folder_id": str(foreign_folder.id),
        },
    )

    assert response.status_code == 404
    assert (await session.scalars(select(Feed))).all() == []


async def test_a_feed_can_be_filed_in_an_own_folder(client: httpx.AsyncClient) -> None:
    headers = await _admin_headers(client)
    folder = (await client.post("/folders", headers=headers, json={"name": "News"})).json()

    response = await client.post(
        "/feeds",
        headers=headers,
        json={"title": "Mine", "url": "https://example.com/rss", "folder_id": folder["id"]},
    )

    assert response.status_code == 201
    assert response.json()["folder_id"] == folder["id"]


async def test_the_database_refuses_a_second_subscription_to_the_same_source(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _admin_headers(client)
    user = (await session.scalars(select(User))).one()
    for _ in range(2):
        session.add(
            Feed(
                user_id=user.id,
                source_type=SourceType.MINIFLUX,
                external_feed_id="9",
                title="Dup",
                url="https://example.com/dup",
            )
        )

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_two_readers_may_subscribe_to_the_same_source(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await _admin_headers(client)
    admin = (await session.scalars(select(User))).one()
    other = await _other_user(session)
    for user in (admin, other):
        session.add(
            Feed(
                user_id=user.id,
                source_type=SourceType.MINIFLUX,
                external_feed_id="9",
                title="Shared",
                url="https://example.com/shared",
            )
        )

    await session.commit()

    assert len((await session.scalars(select(Feed))).all()) == 2


async def test_a_token_of_another_user_is_not_needed_to_list_only_own_feeds(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    headers = await _admin_headers(client)
    other = await _other_user(session)
    other_headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}
    await client.post(
        "/feeds", headers=other_headers, json={"title": "T", "url": "https://x.test/rss"}
    )

    assert (await client.get("/feeds", headers=headers)).json() == []
