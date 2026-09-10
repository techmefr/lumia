"""Grafting Lumia onto a Miniflux that was already running, with feeds of its own.

A reader who has used Miniflux for years has feeds there that no Lumia row knows about. Adding
one of them from Lumia must attach to the feed already in place rather than ask Miniflux for a
second copy of it — Miniflux refuses a duplicate URL outright, so without this the feed simply
cannot be added at all.
"""

from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.models import Feed, Folder
from api.domain.feed.opml_service import add_feed, import_opml
from api.domain.user.models import Instance, User
from config.database import get_engine

EXISTING_URL = "https://lwn.net/headlines/rss"

# What GET /v1/feeds answers on an instance that has been running for years.
EXISTING_FEEDS = [
    {
        "id": 42,
        "title": "LWN.net",
        "feed_url": EXISTING_URL,
        "category": {"id": 3, "title": "Linux"},
    }
]

OPML_FOR_THE_EXISTING_FEED = f"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <body>
    <outline type="rss" text="LWN" title="LWN" xmlUrl="{EXISTING_URL}"/>
  </body>
</opml>
""".encode()


def _populated_miniflux(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/v1/feeds":
        return httpx.Response(200, json=EXISTING_FEEDS)
    if request.method == "GET" and request.url.path == "/v1/categories":
        return httpx.Response(200, json=[{"id": 3, "title": "Linux"}])
    if request.method == "GET" and request.url.path == "/v1/feeds/42":
        return httpx.Response(200, json={"id": 42, "title": "LWN.net"})
    if request.method == "POST" and request.url.path == "/v1/feeds":
        # Miniflux refuses a URL it already carries; a second copy is not on offer.
        return httpx.Response(400, json={"error_message": "This feed already exists."})
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


async def test_adding_a_feed_miniflux_already_carries_attaches_to_it(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)

    feed = await add_feed(
        session,
        user,
        EXISTING_URL,
        None,
        miniflux_transport=httpx.MockTransport(_populated_miniflux),
    )

    assert feed.external_feed_id == "42"
    assert feed.title == "LWN.net"
    assert feed.url == EXISTING_URL


async def test_attaching_does_not_ask_miniflux_for_a_second_copy(session: AsyncSession) -> None:
    user = await _create_user(session)
    posted: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/feeds":
            posted.append(str(request.url))
        return _populated_miniflux(request)

    await add_feed(
        session, user, EXISTING_URL, None, miniflux_transport=httpx.MockTransport(handler)
    )

    assert posted == []


async def test_a_feed_miniflux_does_not_have_is_still_created(session: AsyncSession) -> None:
    """Attaching must not become the only path: an unknown URL is still registered."""
    user = await _create_user(session)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v1/feeds":
            return httpx.Response(200, json=EXISTING_FEEDS)
        if request.method == "POST" and request.url.path == "/v1/feeds":
            return httpx.Response(201, json={"feed_id": 7})
        if request.method == "GET" and request.url.path == "/v1/feeds/7":
            return httpx.Response(200, json={"id": 7, "title": "Hacker News"})
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    feed = await add_feed(
        session,
        user,
        "https://hnrss.org/frontpage",
        None,
        miniflux_transport=httpx.MockTransport(handler),
    )

    assert feed.external_feed_id == "7"


async def test_a_trailing_slash_is_not_a_different_feed(session: AsyncSession) -> None:
    """Miniflux stores the URL it was given; a reader typing the same address with a trailing
    slash must not end up unable to add it."""
    user = await _create_user(session)

    feed = await add_feed(
        session,
        user,
        EXISTING_URL + "/",
        None,
        miniflux_transport=httpx.MockTransport(_populated_miniflux),
    )

    assert feed.external_feed_id == "42"


async def test_two_readers_can_both_attach_to_one_miniflux_feed(session: AsyncSession) -> None:
    """One Miniflux feed, one row per reader: that is what makes a shared instance work."""
    first = await _create_user(session)
    second = await _create_user(session)

    for reader in (first, second):
        await add_feed(
            session,
            reader,
            EXISTING_URL,
            None,
            miniflux_transport=httpx.MockTransport(_populated_miniflux),
        )

    rows = (await session.scalars(select(Feed).where(Feed.url == EXISTING_URL))).all()
    assert {row.user_id for row in rows} == {first.id, second.id}
    assert {row.external_feed_id for row in rows} == {"42"}


async def test_an_opml_import_attaches_to_the_feeds_miniflux_already_carries(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)

    created = await import_opml(
        session,
        user,
        OPML_FOR_THE_EXISTING_FEED,
        miniflux_transport=httpx.MockTransport(_populated_miniflux),
    )

    assert [feed.external_feed_id for feed in created] == ["42"]
    assert await session.scalar(select(func.count()).select_from(Folder)) == 0
