from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.playlist.duration_service import build_for_duration
from api.domain.recommendation.models import (
    FilterMode,
    UserArticleFeedback,
    UserFeedScore,
    UserFilterRule,
)
from api.domain.user.models import Instance, User
from config.database import get_engine

#: 200 words per minute, so this is a five-minute article.
_FIVE_MINUTES = " ".join(["mot"] * 1000)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _user(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id, email="user@example.com", username="user", password_hash=None
    )
    session.add(user)
    await session.commit()
    return user


async def _feed(session: AsyncSession, user: User, *, external_feed_id: str = "10") -> Feed:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=external_feed_id,
        title=f"Feed {external_feed_id}",
        url=f"https://example.com/{external_feed_id}/feed",
    )
    session.add(feed)
    await session.commit()
    return feed


async def _article(
    session: AsyncSession,
    feed: Feed,
    *,
    external_entry_id: str,
    title: str = "Article",
    content: str = _FIVE_MINUTES,
) -> Article:
    article = Article(
        feed_id=feed.id,
        external_entry_id=external_entry_id,
        title=title,
        url=f"https://example.com/{external_entry_id}",
        content=content,
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.commit()
    return article


async def test_build_for_duration_stops_at_the_budget(session: AsyncSession) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    for index in range(5):
        await _article(session, feed, external_entry_id=str(index))

    playlist = await build_for_duration(session, user.id, target_minutes=12)

    # Five-minute articles, so two fit and the third would overflow.
    assert len(playlist.items) == 2


async def test_build_for_duration_names_the_playlist_with_the_duration(
    session: AsyncSession,
) -> None:
    user = await _user(session)

    playlist = await build_for_duration(session, user.id, target_minutes=25)

    assert playlist.name.startswith("25 min · ")


async def test_build_for_duration_skips_articles_already_read(session: AsyncSession) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    read = await _article(session, feed, external_entry_id="1")
    unread = await _article(session, feed, external_entry_id="2")
    session.add(UserArticleFeedback(user_id=user.id, article_id=read.id, read=True))
    await session.commit()

    playlist = await build_for_duration(session, user.id, target_minutes=45)

    assert [item.article_id for item in playlist.items] == [unread.id]


async def test_build_for_duration_drops_a_muted_article(session: AsyncSession) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    await _article(session, feed, external_entry_id="1", title="Le prix du Bitcoin")
    kept = await _article(session, feed, external_entry_id="2", title="Un titre neutre")
    session.add(UserFilterRule(user_id=user.id, term="bitcoin", mode=FilterMode.MUTE))
    await session.commit()

    playlist = await build_for_duration(session, user.id, target_minutes=45)

    assert [item.article_id for item in playlist.items] == [kept.id]


async def test_build_for_duration_takes_the_best_scored_first(session: AsyncSession) -> None:
    user = await _user(session)
    liked_feed = await _feed(session, user, external_feed_id="10")
    other_feed = await _feed(session, user, external_feed_id="20")
    ignored = await _article(session, other_feed, external_entry_id="1")
    wanted = await _article(session, liked_feed, external_entry_id="2")
    session.add(UserFeedScore(user_id=user.id, feed_id=liked_feed.id, score=3.0))
    await session.commit()

    # Room for a single five-minute article, so the ranking decides which one.
    playlist = await build_for_duration(session, user.id, target_minutes=5)

    assert [item.article_id for item in playlist.items] == [wanted.id]
    assert ignored.id not in [item.article_id for item in playlist.items]


async def test_build_for_duration_returns_an_empty_playlist_when_nothing_fits(
    session: AsyncSession,
) -> None:
    user = await _user(session)
    feed = await _feed(session, user)
    await _article(session, feed, external_entry_id="1", content=" ".join(["mot"] * 20_000))

    playlist = await build_for_duration(session, user.id, target_minutes=5)

    assert playlist.items == []


async def test_build_for_duration_ignores_another_users_articles(session: AsyncSession) -> None:
    user = await _user(session)
    other = User(
        instance_id=user.instance_id,
        email="other@example.com",
        username="other",
        password_hash=None,
    )
    session.add(other)
    await session.commit()
    other_feed = await _feed(session, other, external_feed_id="30")
    await _article(session, other_feed, external_entry_id="1")

    playlist = await build_for_duration(session, user.id, target_minutes=45)

    assert playlist.items == []
