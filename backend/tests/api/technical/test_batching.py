from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article import scope as scope_module
from api.domain.article.models import Article
from api.domain.article.scope import resolve_scope_article_ids
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation import bulk_feedback_service
from api.domain.recommendation.bulk_feedback_service import FeedbackAxis, set_feedback_axis
from api.domain.recommendation.models import UserArticleFeedback
from api.domain.user import account_service
from api.domain.user.account_service import delete_account
from api.domain.user.models import Instance, User
from api.technical.batching import MAX_BIND_BATCH, chunked
from config.database import get_engine


def test_a_list_is_cut_into_slices_of_at_most_the_requested_size() -> None:
    assert [list(batch) for batch in chunked(list(range(5)), 2)] == [[0, 1], [2, 3], [4]]


def test_an_empty_list_yields_nothing() -> None:
    assert list(chunked([], 2)) == []


def test_the_default_slice_stays_far_below_the_driver_parameter_ceiling() -> None:
    assert MAX_BIND_BATCH <= 10_000


def _small_batches(items: list, size: int = 2):  # type: ignore[no-untyped-def,type-arg]
    return chunked(items, 2)


@pytest.fixture
async def session(db_schema: None) -> AsyncSession:  # type: ignore[misc]
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as async_session:
        yield async_session


async def _reader_with_articles(session: AsyncSession, count: int) -> tuple[User, list[Article]]:
    instance = Instance(max_accounts=5, disk_quota_mb=1024)
    session.add(instance)
    await session.flush()
    reader = User(instance_id=instance.id, email="reader@example.com", username="reader")
    session.add(reader)
    await session.flush()
    feed = Feed(
        user_id=reader.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="1",
        title="Blog",
        url="https://blog.test/rss",
    )
    session.add(feed)
    await session.flush()
    articles = [
        Article(
            feed_id=feed.id,
            external_entry_id=str(index),
            title=f"Article {index}",
            url=f"https://blog.test/{index}",
            content="Body",
            published_at=datetime(2026, 8, 12, tzinfo=UTC),
        )
        for index in range(count)
    ]
    session.add_all(articles)
    await session.commit()
    return reader, articles


async def test_a_scope_wider_than_one_batch_still_resolves_every_article(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scope_module, "chunked", _small_batches)
    reader, articles = await _reader_with_articles(session, 5)
    wanted = [article.id for article in articles] + [uuid4()]

    resolved = await resolve_scope_article_ids(session, reader.id, article_ids=wanted)

    assert sorted(resolved) == sorted(article.id for article in articles)


async def test_a_bulk_feedback_wider_than_one_batch_updates_every_article(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bulk_feedback_service, "chunked", _small_batches)
    reader, articles = await _reader_with_articles(session, 5)
    ids = [article.id for article in articles]
    await set_feedback_axis(session, reader.id, ids[:3], axis=FeedbackAxis.SAVED, value=True)

    changed = await set_feedback_axis(session, reader.id, ids, axis=FeedbackAxis.SAVED, value=True)

    assert sorted(changed) == sorted(ids[3:])
    saved = await session.scalar(
        select(func.count()).select_from(UserArticleFeedback).where(UserArticleFeedback.saved)
    )
    assert saved == 5


async def test_deleting_an_account_with_more_articles_than_one_batch_removes_them_all(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(account_service, "chunked", _small_batches)
    reader, _ = await _reader_with_articles(session, 5)

    await delete_account(session, reader.id)

    assert await session.scalar(select(func.count()).select_from(Article)) == 0
    assert await session.scalar(select(func.count()).select_from(Feed)) == 0
    assert await session.scalar(select(func.count()).select_from(User)) == 0
