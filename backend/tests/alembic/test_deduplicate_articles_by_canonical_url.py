import importlib.util
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.playlist.models import Playlist, PlaylistItem
from api.domain.recommendation.models import UserArticleFeedback, Vote
from api.domain.user.models import Instance, User
from config.database import get_engine

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "d5c1a70e82b4_deduplicate_articles_by_canonical_url.py"
)


def _load_collapse_duplicates() -> Callable[[Connection], None]:
    spec = importlib.util.spec_from_file_location("migration_under_test", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    collapse: Callable[[Connection], None] = module._collapse_duplicates
    return collapse


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _run_migration_step() -> None:
    async with get_engine().begin() as connection:
        await connection.run_sync(_load_collapse_duplicates())


async def _create_user(session: AsyncSession, *, email: str) -> User:
    instance = await session.scalar(select(Instance))
    if instance is None:
        instance = Instance(max_accounts=10, disk_quota_mb=1000)
        session.add(instance)
        await session.flush()
    user = User(
        instance_id=instance.id,
        email=email,
        username=email.split("@")[0],
        password_hash=None,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_feed(session: AsyncSession, user: User, *, external_feed_id: str) -> Feed:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_feed_id,
        title="Feed",
        url=f"https://example.com/{external_feed_id}",
    )
    session.add(feed)
    await session.flush()
    return feed


async def _create_article(session: AsyncSession, feed: Feed, **overrides: Any) -> Article:
    defaults: dict[str, Any] = {
        "feed_id": feed.id,
        "external_entry_id": "entry",
        "title": "Une depeche",
        "url": "https://example.com/depeche",
        "content": "Le contenu de la depeche.",
        "published_at": datetime(2026, 8, 12, 10, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    article = Article(**defaults)
    session.add(article)
    await session.flush()
    return article


async def test_it_keeps_the_earliest_published_copy_of_a_readers_duplicate(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, email="reader@example.com")
    original_feed = await _create_feed(session, user, external_feed_id="1")
    mirror_feed = await _create_feed(session, user, external_feed_id="2")
    original = await _create_article(
        session,
        original_feed,
        external_entry_id="1",
        published_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
    )
    await _create_article(
        session,
        mirror_feed,
        external_entry_id="2",
        url="http://www.example.com/depeche/?utm_source=mirror",
        published_at=datetime(2026, 8, 30, 9, 0, tzinfo=UTC),
    )
    await session.commit()

    await _run_migration_step()

    articles = list(await session.scalars(select(Article)))
    assert [article.id for article in articles] == [original.id]


async def test_it_leaves_the_same_url_alone_when_two_readers_hold_it(
    session: AsyncSession,
) -> None:
    first = await _create_user(session, email="first@example.com")
    second = await _create_user(session, email="second@example.com")
    await _create_article(session, await _create_feed(session, first, external_feed_id="1"))
    await _create_article(session, await _create_feed(session, second, external_feed_id="1"))
    await session.commit()

    await _run_migration_step()

    assert len(list(await session.scalars(select(Article)))) == 2


async def test_it_carries_reading_state_and_feedback_over_to_the_survivor(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, email="reader@example.com")
    keeper = await _create_article(
        session,
        await _create_feed(session, user, external_feed_id="1"),
        published_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
    )
    loser = await _create_article(
        session,
        await _create_feed(session, user, external_feed_id="2"),
        external_entry_id="2",
        url="https://example.com/depeche?utm_campaign=rss",
        published_at=datetime(2026, 8, 30, 9, 0, tzinfo=UTC),
    )
    session.add(
        UserArticleFeedback(user_id=user.id, article_id=keeper.id, favorite=True, sentiment=None)
    )
    session.add(
        UserArticleFeedback(
            user_id=user.id,
            article_id=loser.id,
            read=True,
            saved=True,
            sentiment=Vote.LIKE,
            scroll_progress=0.8,
        )
    )
    await session.commit()

    await _run_migration_step()

    feedback = list(await session.scalars(select(UserArticleFeedback)))
    assert len(feedback) == 1
    assert feedback[0].article_id == keeper.id
    assert feedback[0].read is True
    assert feedback[0].saved is True
    assert feedback[0].favorite is True
    assert feedback[0].sentiment == Vote.LIKE
    assert feedback[0].scroll_progress == pytest.approx(0.8)


async def test_it_moves_a_lone_feedback_row_rather_than_dropping_it(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, email="reader@example.com")
    keeper = await _create_article(
        session,
        await _create_feed(session, user, external_feed_id="1"),
        published_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
    )
    loser = await _create_article(
        session,
        await _create_feed(session, user, external_feed_id="2"),
        external_entry_id="2",
        url="https://example.com/depeche/",
        published_at=datetime(2026, 8, 30, 9, 0, tzinfo=UTC),
    )
    session.add(UserArticleFeedback(user_id=user.id, article_id=loser.id, read=True))
    await session.commit()

    await _run_migration_step()

    feedback = list(await session.scalars(select(UserArticleFeedback)))
    assert len(feedback) == 1
    assert feedback[0].article_id == keeper.id
    assert feedback[0].read is True


async def test_it_keeps_playlist_membership_and_closes_the_hole_it_leaves(
    session: AsyncSession,
) -> None:
    user = await _create_user(session, email="reader@example.com")
    feed = await _create_feed(session, user, external_feed_id="1")
    mirror = await _create_feed(session, user, external_feed_id="2")
    keeper = await _create_article(
        session, feed, published_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    )
    loser = await _create_article(
        session,
        mirror,
        external_entry_id="2",
        url="https://example.com/depeche?utm_source=mirror",
        published_at=datetime(2026, 8, 30, 9, 0, tzinfo=UTC),
    )
    other = await _create_article(
        session, feed, external_entry_id="3", url="https://example.com/autre"
    )
    playlist = Playlist(user_id=user.id, name="Ecoute")
    session.add(playlist)
    await session.flush()
    session.add(PlaylistItem(playlist_id=playlist.id, article_id=keeper.id, position=0))
    session.add(PlaylistItem(playlist_id=playlist.id, article_id=loser.id, position=1))
    session.add(PlaylistItem(playlist_id=playlist.id, article_id=other.id, position=2))
    await session.commit()

    await _run_migration_step()

    items = list(await session.scalars(select(PlaylistItem).order_by(PlaylistItem.position)))
    assert [(item.article_id, item.position) for item in items] == [
        (keeper.id, 0),
        (other.id, 1),
    ]


async def test_it_moves_a_playlist_entry_the_survivor_was_not_in(session: AsyncSession) -> None:
    user = await _create_user(session, email="reader@example.com")
    keeper = await _create_article(
        session,
        await _create_feed(session, user, external_feed_id="1"),
        published_at=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
    )
    loser = await _create_article(
        session,
        await _create_feed(session, user, external_feed_id="2"),
        external_entry_id="2",
        url="https://example.com/depeche#lire",
        published_at=datetime(2026, 8, 30, 9, 0, tzinfo=UTC),
    )
    playlist = Playlist(user_id=user.id, name="Ecoute")
    session.add(playlist)
    await session.flush()
    session.add(PlaylistItem(playlist_id=playlist.id, article_id=loser.id, position=0))
    await session.commit()

    await _run_migration_step()

    items = list(await session.scalars(select(PlaylistItem)))
    assert [item.article_id for item in items] == [keeper.id]
