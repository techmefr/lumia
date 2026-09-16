from collections.abc import AsyncIterator, Iterator, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user.models import DigestFrequency, Instance, ReadingLang, User
from config.database import get_engine
from worker.domain.digest.send_digests import send_reader_digests

NOW = datetime(2026, 9, 16, 8, 5, tzinfo=UTC)


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _reader(session: AsyncSession, **overrides: object) -> User:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    defaults: dict[str, object] = {
        "digest_frequency": DigestFrequency.DAILY,
        "digest_hour": 8,
        "digest_timezone": "UTC",
    }
    user = User(
        instance_id=instance.id,
        email=f"{uuid4()}@example.com",
        username="reader",
        **{**defaults, **overrides},
    )
    session.add(user)
    await session.commit()
    return user


async def _publish(session: AsyncSession, user: User, title: str, *, age: timedelta) -> Article:
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id=str(uuid4()),
        title="Le Blog",
        url=f"https://blog.test/{uuid4()}",
    )
    session.add(feed)
    await session.flush()
    article = Article(
        feed_id=feed.id,
        external_entry_id=str(uuid4()),
        title=title,
        url=f"https://blog.test/{uuid4()}",
        content="<p>body</p>",
        summary=f"summary of {title}",
        published_at=NOW - age,
    )
    session.add(article)
    await session.commit()
    return article


def _sent(sender: AsyncMock) -> Mapping[str, Any]:
    call = sender.await_args
    assert call is not None
    return call.kwargs


@pytest.fixture
def sender() -> Iterator[AsyncMock]:
    with patch("api.domain.digest.digest_service.send_email", new_callable=AsyncMock) as mocked:
        yield mocked


async def test_a_reader_who_did_not_opt_in_is_never_mailed(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session, digest_frequency=DigestFrequency.NEVER)
    await _publish(session, user, "Something new", age=timedelta(hours=2))

    assert await send_reader_digests({}, now=NOW) == 0
    sender.assert_not_awaited()


async def test_nothing_unread_means_no_mail_at_all(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    article = await _publish(session, user, "Already read", age=timedelta(hours=2))
    session.add(UserArticleFeedback(user_id=user.id, article_id=article.id, read=True))
    await session.commit()

    assert await send_reader_digests({}, now=NOW) == 0
    sender.assert_not_awaited()
    await session.refresh(user)
    # The period stays unspent: a later run in the same day may well find something to report.
    assert user.digest_last_period is None


async def test_a_due_reader_gets_one_mail_and_a_rerun_sends_no_second(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    await _publish(session, user, "Worth reading", age=timedelta(hours=2))

    assert await send_reader_digests({}, now=NOW) == 1
    assert sender.await_count == 1
    await session.refresh(user)
    assert user.digest_last_period == "2026-09-16"
    assert user.digest_last_sent_at is not None

    assert await send_reader_digests({}, now=NOW) == 0
    assert sender.await_count == 1


async def test_the_mail_carries_both_alternatives_and_the_article(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    await _publish(session, user, "Worth reading", age=timedelta(hours=2))

    await send_reader_digests({}, now=NOW)

    kwargs = _sent(sender)
    assert kwargs["to"] == user.email
    assert "Worth reading" in kwargs["body"]
    assert "Worth reading" in kwargs["html_body"]
    assert "<img" not in kwargs["html_body"]


async def test_a_weekly_reader_is_skipped_on_a_day_their_week_was_already_covered(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session, digest_frequency=DigestFrequency.WEEKLY)
    await _publish(session, user, "Worth reading", age=timedelta(days=2))

    assert await send_reader_digests({}, now=NOW) == 1
    await session.refresh(user)
    assert user.digest_last_period == "2026-W38"

    # Two days on, still the same ISO week, so nothing is owed.
    assert await send_reader_digests({}, now=NOW + timedelta(days=2)) == 0
    assert sender.await_count == 1


async def test_the_mail_is_written_in_the_reader_own_language(
    session: AsyncSession, sender: AsyncMock
) -> None:
    german = await _reader(session, preferred_language=ReadingLang.DE)
    await _publish(session, german, "Lesenswert", age=timedelta(hours=2))

    await send_reader_digests({}, now=NOW)

    assert _sent(sender)["subject"] == "Ihre tägliche Lumia-Übersicht"


async def test_a_reader_is_left_alone_outside_the_hour_they_chose(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session, digest_hour=20)
    await _publish(session, user, "Worth reading", age=timedelta(hours=2))

    assert await send_reader_digests({}, now=NOW) == 0
    sender.assert_not_awaited()


async def test_the_best_ranked_article_leads_the_digest(
    session: AsyncSession, sender: AsyncMock
) -> None:
    user = await _reader(session)
    await _publish(session, user, "Older but first", age=timedelta(hours=20))
    await _publish(session, user, "Newer", age=timedelta(hours=1))

    await send_reader_digests({}, now=NOW)

    body = _sent(sender)["body"]
    # Nothing has been voted on, so every score ties at zero and recency decides the order.
    assert body.index("Newer") < body.index("Older but first")
