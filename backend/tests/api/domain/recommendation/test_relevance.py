from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.domain.article.models import Article, ArticleKeyword, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.recommendation.models import (
    FilterMode,
    UserFeedScore,
    UserFilterRule,
    UserKeywordScore,
)
from api.domain.recommendation.relevance import (
    load_rule_terms,
    matches_any_term,
    score_articles,
    to_relevance,
)
from api.domain.user.models import Instance, User
from config.database import get_engine


@pytest.fixture
async def session(db_schema: None) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session


async def _user_and_feed(session: AsyncSession) -> tuple[User, Feed]:
    instance = Instance(max_accounts=10, disk_quota_mb=1000)
    session.add(instance)
    await session.flush()
    user = User(
        instance_id=instance.id, email="user@example.com", username="user", password_hash=None
    )
    session.add(user)
    await session.flush()
    feed = Feed(
        user_id=user.id,
        source_type=SourceType.MINIFLUX,
        external_feed_id="10",
        title="Feed",
        url="https://example.com/feed",
    )
    session.add(feed)
    await session.commit()
    return user, feed


async def _article(
    session: AsyncSession, feed: Feed, *, external_entry_id: str, title: str = "Article"
) -> Article:
    article = Article(
        feed_id=feed.id,
        external_entry_id=external_entry_id,
        title=title,
        url=f"https://example.com/{external_entry_id}",
        content="Content",
        summary="Un résumé",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    session.add(article)
    await session.commit()
    return article


def test_to_relevance_maps_a_neutral_score_to_the_middle() -> None:
    assert to_relevance(0.0) == 50


def test_to_relevance_stays_inside_the_badge_range() -> None:
    assert to_relevance(50.0) == 100
    assert to_relevance(-50.0) == 0


def test_to_relevance_is_monotonic() -> None:
    assert to_relevance(0.5) < to_relevance(1.5) < to_relevance(4.5)


def test_matches_any_term_reads_the_title_and_the_summary_only() -> None:
    article = Article(
        feed_id=None,
        external_entry_id="1",
        title="Le prix du Bitcoin",
        url="https://example.com/1",
        content="<p>un paragraphe sur les fusées</p>",
        summary="marchés",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    assert matches_any_term(article, ["bitcoin"]) is True
    assert matches_any_term(article, ["marchés"]) is True
    assert matches_any_term(article, ["fusées"]) is False


def test_matches_any_term_with_no_term_matches_nothing() -> None:
    article = Article(
        feed_id=None,
        external_entry_id="1",
        title="Titre",
        url="https://example.com/1",
        content="Content",
        published_at=datetime(2026, 8, 12, tzinfo=UTC),
    )
    assert matches_any_term(article, []) is False


async def test_score_articles_returns_nothing_for_an_empty_list(session: AsyncSession) -> None:
    user, _ = await _user_and_feed(session)
    assert await score_articles(session, user.id, []) == {}


async def test_score_articles_averages_the_dimensions(session: AsyncSession) -> None:
    user, feed = await _user_and_feed(session)
    article = await _article(session, feed, external_entry_id="1")
    keyword = Keyword(term="chat", lang=Lang.FR)
    session.add(keyword)
    await session.flush()
    session.add(ArticleKeyword(article_id=article.id, keyword_id=keyword.id, weight=0.5))
    session.add(UserKeywordScore(user_id=user.id, keyword_id=keyword.id, score=3.0))
    session.add(UserFeedScore(user_id=user.id, feed_id=feed.id, score=1.0))
    await session.commit()

    scores = await score_articles(session, user.id, [article])

    # One keyword at 3.0 and the feed at 1.0, nothing else known: (3 + 1) / 2.
    assert scores == {article.id: 2.0}


async def test_score_articles_treats_an_unknown_dimension_as_zero(session: AsyncSession) -> None:
    user, feed = await _user_and_feed(session)
    article = await _article(session, feed, external_entry_id="1")

    scores = await score_articles(session, user.id, [article])

    assert scores == {article.id: 0.0}


async def test_score_articles_adds_the_boost_weight_on_a_matching_rule(
    session: AsyncSession,
) -> None:
    user, feed = await _user_and_feed(session)
    plain = await _article(session, feed, external_entry_id="1", title="Un titre neutre")
    boosted = await _article(session, feed, external_entry_id="2", title="Le futur du Bitcoin")
    session.add(UserFilterRule(user_id=user.id, term="bitcoin", mode=FilterMode.BOOST))
    await session.commit()

    scores = await score_articles(session, user.id, [plain, boosted])

    assert scores[plain.id] == 0.0
    assert scores[boosted.id] == 1.0


async def test_load_rule_terms_only_returns_the_asked_mode(session: AsyncSession) -> None:
    user, _ = await _user_and_feed(session)
    session.add(UserFilterRule(user_id=user.id, term="bitcoin", mode=FilterMode.BOOST))
    session.add(UserFilterRule(user_id=user.id, term="football", mode=FilterMode.MUTE))
    await session.commit()

    assert await load_rule_terms(session, user.id, FilterMode.BOOST) == ["bitcoin"]
    assert await load_rule_terms(session, user.id, FilterMode.MUTE) == ["football"]
