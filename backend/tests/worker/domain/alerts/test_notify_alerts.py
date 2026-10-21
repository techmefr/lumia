from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import FilterMode, UserFilterRule
from api.domain.saved_search.models import AlertNotification, SavedSearch
from api.domain.user.models import Instance, ReadingLang, User
from config.database import get_engine
from worker.domain.pipeline.enrich_article import enrich_article
from worker.technical.connectors.base import RawArticle

CONTENT = (
    "<p>Le chat est dans le jardin avec la souris et il mangeait des croquettes. "
    "Le jardin est grand et le chat aime jouer avec la souris dans le jardin. "
    "Une troisieme phrase decrit encore le chat et le jardin en detail ici.</p>"
)


class _PassThroughExtractor:
    async def extract(self, url: str, fallback_html: str) -> str:
        return fallback_html


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(get_engine(), expire_on_commit=False)() as db_session:
        yield db_session


async def _reader_with_two_feeds(session: AsyncSession) -> tuple[User, Feed, Feed]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id,
        email="user@example.com",
        username="user",
        password_hash=None,
        preferred_language=ReadingLang.FR,
    )
    session.add(user)
    await session.flush()
    feeds = [
        Feed(
            user_id=user.id,
            source_type=SourceType.MINIFLUX,
            external_feed_id=external_id,
            title=f"Feed {external_id}",
            url=f"https://example.com/{external_id}",
        )
        for external_id in ("10", "20")
    ]
    session.add_all(feeds)
    await session.commit()
    return user, feeds[0], feeds[1]


def _search(user: User, **fields: object) -> SavedSearch:
    defaults: dict[str, object] = {"name": "Chat", "query": "chat", "alert": True}
    defaults.update(fields)
    return SavedSearch(user_id=user.id, **defaults)


async def _ingest(feed_external_id: str = "10", entry_id: str = "1") -> None:
    raw = RawArticle(
        source_type="miniflux",
        feed_external_id=feed_external_id,
        external_entry_id=entry_id,
        title="Le chat et le jardin",
        url=f"https://example.com/article-{entry_id}",
        content=CONTENT,
        published_at=datetime(2026, 8, 12, 10, 0, tzinfo=UTC),
        author_name=None,
        category_name=None,
    )
    await enrich_article({}, raw, content_extractor=_PassThroughExtractor())


async def _notifications(session: AsyncSession) -> list[AlertNotification]:
    return list(await session.scalars(select(AlertNotification)))


async def test_a_matching_article_notifies_the_reader(session: AsyncSession) -> None:
    user, _, _ = await _reader_with_two_feeds(session)
    search = _search(user)
    session.add(search)
    await session.commit()

    await _ingest()

    notifications = await _notifications(session)
    article = await session.scalar(select(Article))
    assert article is not None
    assert [(n.user_id, n.saved_search_id, n.article_id, n.read) for n in notifications] == [
        (user.id, search.id, article.id, False)
    ]


async def test_an_article_that_does_not_match_notifies_nobody(session: AsyncSession) -> None:
    user, _, _ = await _reader_with_two_feeds(session)
    session.add(_search(user, query="kubernetes"))
    await session.commit()

    await _ingest()

    assert await _notifications(session) == []


async def test_a_saved_search_that_is_not_an_alert_stays_quiet(session: AsyncSession) -> None:
    user, _, _ = await _reader_with_two_feeds(session)
    session.add(_search(user, alert=False))
    await session.commit()

    await _ingest()

    assert await _notifications(session) == []


async def test_the_scope_of_the_alert_is_respected(session: AsyncSession) -> None:
    user, _, second_feed = await _reader_with_two_feeds(session)
    session.add(_search(user, feed_id=second_feed.id))
    await session.commit()

    await _ingest(feed_external_id="10")
    assert await _notifications(session) == []

    await _ingest(feed_external_id="20", entry_id="2")
    assert len(await _notifications(session)) == 1


async def test_a_muted_term_silences_the_alert(session: AsyncSession) -> None:
    user, _, _ = await _reader_with_two_feeds(session)
    session.add_all(
        [_search(user), UserFilterRule(user_id=user.id, term="jardin", mode=FilterMode.MUTE)]
    )
    await session.commit()

    await _ingest()

    assert await _notifications(session) == []


async def test_reprocessing_an_article_does_not_notify_twice(session: AsyncSession) -> None:
    user, _, _ = await _reader_with_two_feeds(session)
    session.add(_search(user))
    await session.commit()

    await _ingest()
    await _ingest()

    assert len(await _notifications(session)) == 1


async def test_two_alerts_matching_the_same_article_each_notify(session: AsyncSession) -> None:
    user, _, _ = await _reader_with_two_feeds(session)
    session.add_all([_search(user), _search(user, name="Jardin", query="jardin")])
    await session.commit()

    await _ingest()

    assert len(await _notifications(session)) == 2
