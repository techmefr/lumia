from collections.abc import AsyncIterator, Iterator, Mapping
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.saved_search.alert_service import evaluate_alerts_for_new_article
from api.domain.saved_search.models import SavedSearch, SavedSearchMatch
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


def _sent(sender: AsyncMock) -> Mapping[str, Any]:
    call = sender.await_args
    assert call is not None
    return call.kwargs


@pytest.fixture
def sender() -> Iterator[AsyncMock]:
    with patch(
        "api.domain.saved_search.alert_service.send_email", new_callable=AsyncMock
    ) as mocked:
        yield mocked


async def _reader(session: AsyncSession) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email=f"{uuid4()}@example.com",
        username="reader",
    )
    session.add(user)
    await session.commit()
    return user


async def _feed(session: AsyncSession, user: User, title: str = "Le Blog") -> Feed:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=str(uuid4()),
        title=title,
        url=f"https://blog.test/{uuid4()}",
    )
    session.add(feed)
    await session.flush()
    return feed


async def _article(
    session: AsyncSession, feed: Feed, *, title: str, content: str = "<p>x</p>"
) -> Article:
    article = Article(
        feed_id=feed.id,
        external_entry_id=str(uuid4()),
        title=title,
        url=f"https://blog.test/{uuid4()}",
        content=content,
        summary=None,
    )
    session.add(article)
    await session.flush()
    return article


async def test_a_matching_article_triggers_one_mail(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    feed = await _feed(session, user)
    alert = SavedSearch(user_id=user.id, name="rust", query="rust", is_alert=True)
    session.add(alert)
    await session.commit()

    article = await _article(session, feed, title="Learning Rust this week")
    await evaluate_alerts_for_new_article(session, article, user_id=user.id, feed_title=feed.title)
    await session.commit()

    sender.assert_awaited_once()
    assert _sent(sender)["to"] == user.email
    matches = list(await session.scalars(select(SavedSearchMatch)))
    assert len(matches) == 1
    assert matches[0].article_id == article.id


async def test_a_non_matching_article_sends_nothing(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    feed = await _feed(session, user)
    alert = SavedSearch(user_id=user.id, name="rust", query="rust", is_alert=True)
    session.add(alert)
    await session.commit()

    article = await _article(session, feed, title="Cooking pasta tonight")
    await evaluate_alerts_for_new_article(session, article, user_id=user.id, feed_title=feed.title)
    await session.commit()

    sender.assert_not_awaited()
    assert list(await session.scalars(select(SavedSearchMatch))) == []


async def test_a_saved_search_without_the_alert_flag_never_mails(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    feed = await _feed(session, user)
    saved = SavedSearch(user_id=user.id, name="rust", query="rust", is_alert=False)
    session.add(saved)
    await session.commit()

    article = await _article(session, feed, title="Learning Rust this week")
    await evaluate_alerts_for_new_article(session, article, user_id=user.id, feed_title=feed.title)
    await session.commit()

    sender.assert_not_awaited()


async def test_the_same_article_is_never_notified_twice(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    feed = await _feed(session, user)
    alert = SavedSearch(user_id=user.id, name="rust", query="rust", is_alert=True)
    session.add(alert)
    await session.commit()
    article = await _article(session, feed, title="Learning Rust this week")

    await evaluate_alerts_for_new_article(session, article, user_id=user.id, feed_title=feed.title)
    await session.commit()
    # A retried ingestion (or any second evaluation) of the same article must not re-notify.
    await evaluate_alerts_for_new_article(session, article, user_id=user.id, feed_title=feed.title)
    await session.commit()

    assert sender.await_count == 1
    assert len(list(await session.scalars(select(SavedSearchMatch)))) == 1


async def test_an_alert_scoped_to_another_feed_is_not_triggered(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    matching_feed = await _feed(session, user, title="Tech feed")
    other_feed = await _feed(session, user, title="Other feed")
    alert = SavedSearch(user_id=user.id, name="tech only", feed_id=matching_feed.id, is_alert=True)
    session.add(alert)
    await session.commit()

    article = await _article(session, other_feed, title="Anything")
    await evaluate_alerts_for_new_article(
        session, article, user_id=user.id, feed_title=other_feed.title
    )
    await session.commit()

    sender.assert_not_awaited()
