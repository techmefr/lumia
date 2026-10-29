import importlib.util
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.instance.models import AccessRequest
from api.domain.recommendation.models import UserFeedScore
from api.domain.saved_search.models import SavedSearch
from api.domain.user.models import Instance, Invitation, User
from config.database import get_engine

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "b2c5d8e01f32_unique_feeds_emails_and_magic_link_purpose.py"
)


def _load(name: str) -> Callable[[Connection], None]:
    spec = importlib.util.spec_from_file_location("migration_under_test", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    step: Callable[[Connection], None] = getattr(module, name)
    return step


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with get_engine().begin() as connection:
        await connection.execute(
            text("ALTER TABLE feeds DROP CONSTRAINT uq_feeds_user_source_external")
        )
        await connection.execute(text("DROP INDEX uq_users_email_lower"))
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _run(name: str) -> None:
    async with get_engine().begin() as connection:
        await connection.run_sync(_load(name))


async def _user(session: AsyncSession, email: str, *, age_days: int = 0) -> User:
    instance = await session.scalar(select(Instance))
    if instance is None:
        instance = Instance(max_accounts=10, disk_quota_mb=1000)
        session.add(instance)
        await session.flush()
    user = User(
        instance_id=instance.id,
        email=email,
        username=email.split("@")[0],
        created_at=datetime.now(UTC) - timedelta(days=age_days),
    )
    session.add(user)
    await session.flush()
    return user


async def _feed(session: AsyncSession, user: User, *, age_days: int, url: str) -> Feed:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="7",
        title="Feed",
        url=url,
        created_at=datetime.now(UTC) - timedelta(days=age_days),
    )
    session.add(feed)
    await session.flush()
    return feed


def _article(feed: Feed, entry: str) -> Article:
    return Article(
        feed_id=feed.id,
        external_entry_id=entry,
        title=entry,
        url=f"https://example.com/{entry}",
        content="Body",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )


async def test_duplicate_subscriptions_collapse_onto_the_oldest_and_keep_their_articles(
    session: AsyncSession,
) -> None:
    user = await _user(session, "a@example.com")
    oldest = await _feed(session, user, age_days=10, url="https://example.com/a")
    newer = await _feed(session, user, age_days=5, url="https://example.com/b")
    newest = await _feed(session, user, age_days=1, url="https://example.com/c")
    session.add_all([_article(newer, "n1"), _article(newest, "n2"), _article(oldest, "o1")])
    session.add(SavedSearch(user_id=user.id, name="s", query="q", feed_id=newest.id))
    session.add_all(
        [
            UserFeedScore(user_id=user.id, feed_id=oldest.id, score=1.0),
            UserFeedScore(user_id=user.id, feed_id=newer.id, score=2.0),
        ]
    )
    await session.commit()

    await _run("_merge_duplicate_feeds")

    session.expire_all()
    feeds = (await session.scalars(select(Feed))).all()
    assert [feed.id for feed in feeds] == [oldest.id]
    articles = (await session.scalars(select(Article))).all()
    assert {article.feed_id for article in articles} == {oldest.id}
    assert len(articles) == 3
    search = (await session.scalars(select(SavedSearch))).one()
    assert search.feed_id == oldest.id
    scores = (await session.scalars(select(UserFeedScore))).all()
    assert [(score.feed_id, score.score) for score in scores] == [(oldest.id, 1.0)]


async def test_the_same_source_held_by_two_readers_is_left_alone(session: AsyncSession) -> None:
    first = await _user(session, "a@example.com")
    second = await _user(session, "b@example.com")
    await _feed(session, first, age_days=2, url="https://example.com/a")
    await _feed(session, second, age_days=1, url="https://example.com/a")
    await session.commit()

    await _run("_merge_duplicate_feeds")

    assert len((await session.scalars(select(Feed))).all()) == 2


async def test_emails_are_lowercased_and_collisions_get_a_distinct_address(
    session: AsyncSession,
) -> None:
    keeper = await _user(session, "Reader@Example.com", age_days=3)
    twin = await _user(session, "READER@example.com", age_days=2)
    other = await _user(session, "Other@Example.com", age_days=1)
    await session.commit()

    await _run("_lowercase_emails")

    session.expire_all()
    emails = {user.id: user.email for user in (await session.scalars(select(User))).all()}
    assert emails[keeper.id] == "reader@example.com"
    assert emails[twin.id] == "reader+duplicate2@example.com"
    assert emails[other.id] == "other@example.com"
    assert len(set(emails.values())) == 3


async def test_invitations_and_access_requests_are_lowercased_and_deduplicated(
    session: AsyncSession,
) -> None:
    admin = await _user(session, "admin@example.com")
    session.add(
        Invitation(
            instance_id=admin.instance_id,
            email="Guest@Example.com",
            token="t" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    session.add_all(
        [
            AccessRequest(
                email="Visitor@Example.com",
                username="first",
                created_at=datetime.now(UTC) - timedelta(days=2),
            ),
            AccessRequest(
                email="visitor@example.com",
                username="second",
                created_at=datetime.now(UTC) - timedelta(days=1),
            ),
        ]
    )
    await session.commit()

    await _run("_lowercase_emails")

    session.expire_all()
    assert (await session.scalars(select(Invitation.email))).one() == "guest@example.com"
    remaining: Any = (await session.scalars(select(AccessRequest))).all()
    assert [(request.email, request.username) for request in remaining] == [
        ("visitor@example.com", "first")
    ]
