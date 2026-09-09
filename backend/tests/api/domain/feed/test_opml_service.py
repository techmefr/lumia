from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.models import Feed, Folder
from api.domain.feed.opml_service import import_opml
from api.domain.user.models import Instance, User
from config.database import get_engine

FEEDLY_OPML = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <body>
    <outline text="Tech" title="Tech">
      <outline type="rss" text="Hacker News" title="Hacker News"
               xmlUrl="https://hnrss.org/frontpage" htmlUrl="https://news.ycombinator.com"/>
    </outline>
    <outline type="rss" text="Uncategorized Feed" title="Uncategorized Feed"
             xmlUrl="https://example.com/feed.xml" htmlUrl="https://example.com"/>
  </body>
</opml>
"""

MINIFLUX_CATEGORIES = [{"id": 1, "title": "All"}]


def _miniflux_handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and request.url.path == "/v1/categories":
        return httpx.Response(200, json=MINIFLUX_CATEGORIES)
    if request.method == "POST" and request.url.path == "/v1/categories":
        return httpx.Response(201, json={"id": 2, "title": "Tech"})
    if request.method == "POST" and request.url.path == "/v1/feeds":
        return httpx.Response(201, json={"feed_id": 7})
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


async def test_import_opml_creates_folders_and_feeds(session: AsyncSession) -> None:
    user = await _create_user(session)

    feeds = await import_opml(
        session, user, FEEDLY_OPML, miniflux_transport=httpx.MockTransport(_miniflux_handler)
    )

    assert {feed.url for feed in feeds} == {
        "https://hnrss.org/frontpage",
        "https://example.com/feed.xml",
    }

    tech_folder = await session.scalar(
        select(Folder).where(Folder.user_id == user.id, Folder.name == "Tech")
    )
    assert tech_folder is not None

    hn_feed = next(feed for feed in feeds if feed.url == "https://hnrss.org/frontpage")
    assert hn_feed.folder_id == tech_folder.id
    uncategorized_feed = next(feed for feed in feeds if feed.url == "https://example.com/feed.xml")
    assert uncategorized_feed.folder_id is None


async def test_import_opml_skips_a_url_the_user_already_has(session: AsyncSession) -> None:
    user = await _create_user(session)
    existing = Feed(
        user_id=user.id,
        source_type="miniflux",
        external_feed_id="999",
        title="Already there",
        url="https://example.com/feed.xml",
    )
    session.add(existing)
    await session.commit()

    feeds = await import_opml(
        session, user, FEEDLY_OPML, miniflux_transport=httpx.MockTransport(_miniflux_handler)
    )

    assert {feed.url for feed in feeds} == {"https://hnrss.org/frontpage"}
    all_feeds = (await session.scalars(select(Feed).where(Feed.user_id == user.id))).all()
    assert len(all_feeds) == 2


async def test_import_opml_skips_a_feed_that_fails_to_register_with_miniflux(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)

    def handler(request: httpx.Request) -> httpx.Response:
        is_failing_feed_registration = (
            request.method == "POST"
            and request.url.path == "/v1/feeds"
            and b"hnrss" in request.content
        )
        if is_failing_feed_registration:
            return httpx.Response(502, text="upstream feed unreachable")
        return _miniflux_handler(request)

    feeds = await import_opml(
        session, user, FEEDLY_OPML, miniflux_transport=httpx.MockTransport(handler)
    )

    assert {feed.url for feed in feeds} == {"https://example.com/feed.xml"}
    all_feeds = (await session.scalars(select(Feed).where(Feed.user_id == user.id))).all()
    assert len(all_feeds) == 1


async def test_import_opml_reuses_an_existing_feed_registered_by_another_user(
    session: AsyncSession,
) -> None:
    other_user = await _create_user(session)
    already_registered = Feed(
        user_id=other_user.id,
        source_type="miniflux",
        external_feed_id="42",
        title="Hacker News",
        url="https://hnrss.org/frontpage",
    )
    session.add(already_registered)
    await session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/feeds":
            assert b"hnrss" not in request.content, "should not re-register a known feed url"
        return _miniflux_handler(request)

    reader = await _create_user(session)
    feeds = await import_opml(
        session, reader, FEEDLY_OPML, miniflux_transport=httpx.MockTransport(handler)
    )

    hn_feed = next(feed for feed in feeds if feed.url == "https://hnrss.org/frontpage")
    assert hn_feed.external_feed_id == "42"
