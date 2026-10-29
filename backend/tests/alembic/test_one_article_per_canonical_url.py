import importlib.util
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Connection, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import (
    ARTICLE_FEED_CANONICAL_INDEX,
    Article,
    ArticleKeyword,
    Keyword,
    Lang,
)
from api.domain.chat.models import ChatMessage, ChatRole
from api.domain.feed.models import Feed, SourceType
from api.domain.highlight.models import Highlight
from api.domain.playlist.models import Playlist, PlaylistItem
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.tag.models import ArticleTag, Tag
from api.domain.user.models import Instance, User
from config.database import get_engine

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "f4d9a1b73c82_one_article_per_canonical_url_in_a_feed.py"
)


def _load_merge() -> Callable[[Connection], None]:
    spec = importlib.util.spec_from_file_location("article_index_migration", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    merge: Callable[[Connection], None] = module._merge_duplicate_articles
    return merge


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _feed(session: AsyncSession) -> tuple[User, Feed]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(instance_id=instance.id, email="a@example.com", username="a")
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="1",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.flush()
    return user, feed


def _article(feed: Feed, entry: str, day: int, url: str = "https://example.com/a") -> Article:
    return Article(
        feed_id=feed.id,
        external_entry_id=entry,
        title=entry,
        url=url,
        content="c",
        published_at=datetime(2026, 10, day, tzinfo=UTC),
    )


async def test_the_index_refuses_the_same_url_twice_in_a_feed(session: AsyncSession) -> None:
    _user, feed = await _feed(session)
    session.add(_article(feed, "a", 1))
    await session.commit()
    session.add(_article(feed, "b", 2, url="https://example.com/a?utm_source=x"))

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_duplicates_are_merged_into_the_earliest_with_every_related_row_carried_over(
    session: AsyncSession,
) -> None:
    user, feed = await _feed(session)
    await session.execute(text(f"DROP INDEX {ARTICLE_FEED_CANONICAL_INDEX}"))
    keeper = _article(feed, "keeper", 1)
    loser = _article(feed, "loser", 2)
    untouched = _article(feed, "other", 3, url="https://example.com/b")
    session.add_all([keeper, loser, untouched])
    keyword = Keyword(term="chat", lang=Lang.FR)
    shared_tag = Tag(user_id=user.id, name="Shared", slug="shared")
    loser_tag = Tag(user_id=user.id, name="Only", slug="only")
    playlist = Playlist(user_id=user.id, name="P")
    session.add_all([keyword, shared_tag, loser_tag, playlist])
    await session.flush()
    session.add_all(
        [
            UserArticleFeedback(user_id=user.id, article_id=keeper.id, read=False, saved=True),
            UserArticleFeedback(user_id=user.id, article_id=loser.id, read=True, favorite=True),
            ArticleKeyword(article_id=keeper.id, keyword_id=keyword.id, weight=1.0),
            ArticleKeyword(article_id=loser.id, keyword_id=keyword.id, weight=2.0),
            ArticleTag(article_id=keeper.id, tag_id=shared_tag.id),
            ArticleTag(article_id=loser.id, tag_id=shared_tag.id),
            ArticleTag(article_id=loser.id, tag_id=loser_tag.id),
            PlaylistItem(playlist_id=playlist.id, article_id=keeper.id, position=0),
            PlaylistItem(playlist_id=playlist.id, article_id=loser.id, position=1),
            PlaylistItem(playlist_id=playlist.id, article_id=untouched.id, position=2),
            Highlight(
                user_id=user.id, article_id=loser.id, quote="q", start_offset=0, end_offset=1
            ),
            ChatMessage(user_id=user.id, article_id=loser.id, role=ChatRole.USER, content="hello"),
        ]
    )
    await session.commit()
    keeper_id, shared_id, only_id, untouched_id = (
        keeper.id,
        shared_tag.id,
        loser_tag.id,
        untouched.id,
    )

    async with get_engine().begin() as connection:
        await connection.run_sync(_load_merge())

    session.expire_all()
    titles = sorted(await session.scalars(select(Article.title)))
    assert titles == ["keeper", "other"]
    feedback = (await session.scalars(select(UserArticleFeedback))).one()
    assert (feedback.article_id, feedback.saved, feedback.read, feedback.favorite) == (
        keeper_id,
        True,
        True,
        True,
    )
    assert await session.scalar(select(func.count()).select_from(ArticleKeyword)) == 1
    tags = {link.tag_id for link in await session.scalars(select(ArticleTag))}
    assert tags == {shared_id, only_id}
    assert all(link.article_id == keeper_id for link in await session.scalars(select(ArticleTag)))
    items = sorted(
        (item.position, item.article_id) for item in await session.scalars(select(PlaylistItem))
    )
    assert items == [(0, keeper_id), (1, untouched_id)]
    assert (await session.scalars(select(Highlight.article_id))).one() == keeper_id
    assert (await session.scalars(select(ChatMessage.article_id))).one() == keeper_id


async def test_the_same_url_in_two_feeds_is_left_alone(session: AsyncSession) -> None:
    user, feed = await _feed(session)
    await session.execute(text(f"DROP INDEX {ARTICLE_FEED_CANONICAL_INDEX}"))
    other = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="2",
        title="Other",
        url="https://example.com/other",
    )
    session.add(other)
    await session.flush()
    session.add_all([_article(feed, "a", 1), _article(other, "b", 2)])
    await session.commit()

    async with get_engine().begin() as connection:
        await connection.run_sync(_load_merge())

    assert await session.scalar(select(func.count()).select_from(Article)) == 2
