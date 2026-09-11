from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.feed.models import Feed, Folder, SourceType
from api.domain.feed.opml_export import export_opml
from api.domain.feed.opml_parser import parse_opml
from api.domain.user.models import Instance, User
from config.database import get_engine


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


async def test_export_opml_puts_filed_and_unfiled_feeds_in_the_right_place(
    session: AsyncSession,
) -> None:
    user = await _create_user(session)
    folder = Folder(user_id=user.id, name="Tech")
    session.add(folder)
    await session.flush()
    session.add(
        Feed(
            user_id=user.id,
            folder_id=folder.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Hacker News",
            url="https://hnrss.org/frontpage",
        )
    )
    session.add(
        Feed(
            user_id=user.id,
            folder_id=None,
            source_type=SourceType.MINIFLUX,
            external_feed_id="2",
            title="Lobsters",
            url="https://lobste.rs/rss",
        )
    )
    await session.commit()

    xml_bytes = await export_opml(session, user)
    entries = parse_opml(xml_bytes)

    assert {(entry.folder_name, entry.url) for entry in entries} == {
        ("Tech", "https://hnrss.org/frontpage"),
        (None, "https://lobste.rs/rss"),
    }


async def test_export_opml_excludes_the_manual_saved_pages_feed(session: AsyncSession) -> None:
    user = await _create_user(session)
    session.add(
        Feed(
            user_id=user.id,
            folder_id=None,
            source_type=SourceType.MANUAL,
            external_feed_id="manual",
            title="Saved pages",
            url="",
        )
    )
    await session.commit()

    xml_bytes = await export_opml(session, user)

    assert parse_opml(xml_bytes) == []


async def test_export_opml_only_includes_the_caller_own_feeds(session: AsyncSession) -> None:
    owner = await _create_user(session)
    other = await _create_user(session)
    session.add(
        Feed(
            user_id=other.id,
            folder_id=None,
            source_type=SourceType.MINIFLUX,
            external_feed_id="1",
            title="Someone else's feed",
            url="https://example.com/other.xml",
        )
    )
    await session.commit()

    xml_bytes = await export_opml(session, owner)

    assert parse_opml(xml_bytes) == []
