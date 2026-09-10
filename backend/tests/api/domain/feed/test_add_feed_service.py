from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.exceptions import FeedUnreachableError, FolderNotFoundError
from api.domain.feed.models import Folder
from api.domain.feed.opml_service import add_feed
from api.domain.user.models import Instance, User
from config.database import get_engine


def _miniflux_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/v1/feeds":
        return httpx.Response(200, json=[])
    if request.method == "GET" and request.url.path == "/v1/categories":
        return httpx.Response(200, json=[])
    if request.method == "POST" and request.url.path == "/v1/categories":
        return httpx.Response(201, json={"id": 2, "title": "Tech"})
    if request.method == "POST" and request.url.path == "/v1/feeds":
        return httpx.Response(201, json={"feed_id": 7})
    if request.method == "GET" and request.url.path == "/v1/feeds/7":
        return httpx.Response(200, json={"id": 7, "title": "Hacker News"})
    raise AssertionError(f"unexpected request {request.method} {request.url}")


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _create_user(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email=f"{uuid4()}@example.com",
        username="reader",
        password_hash="irrelevant",
    )
    session.add(user)
    await session.commit()
    return user


async def test_add_feed_creates_an_unfiled_feed_when_no_folder_is_given(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)

    feed = await add_feed(
        session,
        user,
        "https://hnrss.org/frontpage",
        None,
        miniflux_transport=httpx.MockTransport(_miniflux_handler),
    )

    assert feed.url == "https://hnrss.org/frontpage"
    assert feed.title == "Hacker News"
    assert feed.external_feed_id == "7"
    assert feed.folder_id is None


async def test_add_feed_registers_in_an_existing_folders_miniflux_category(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)
    folder = Folder(user_id=user.id, name="Tech")
    session.add(folder)
    await session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/feeds":
            assert b'"category_id":2' in request.content
        return _miniflux_handler(request)

    feed = await add_feed(
        session,
        user,
        "https://hnrss.org/frontpage",
        folder.id,
        miniflux_transport=httpx.MockTransport(handler),
    )

    assert feed.folder_id == folder.id


async def test_add_feed_raises_when_the_folder_does_not_belong_to_the_user(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)
    other_user = await _create_user(session)
    other_folder = Folder(user_id=other_user.id, name="Tech")
    session.add(other_folder)
    await session.commit()

    with pytest.raises(FolderNotFoundError):
        await add_feed(
            session,
            user,
            "https://hnrss.org/frontpage",
            other_folder.id,
            miniflux_transport=httpx.MockTransport(_miniflux_handler),
        )


async def test_add_feed_raises_when_miniflux_cannot_reach_the_url(session: AsyncSession) -> None:
    user = await _create_user(session)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/feeds":
            return httpx.Response(502, text="upstream feed unreachable")
        return _miniflux_handler(request)

    with pytest.raises(FeedUnreachableError):
        await add_feed(
            session,
            user,
            "https://example.com/broken.xml",
            None,
            miniflux_transport=httpx.MockTransport(handler),
        )
