"""Per-article affinity, shared by L'Étincelle, the article lists and the timed playlists.

The stored scores are unbounded running sums (a like adds 1.5, a dislike removes 0.5, on every
keyword, feed, author and category of the article). That is fine for ranking but meaningless as a
number to show, so `to_relevance` squashes the average through tanh: 50 is "nothing known yet",
100 is "everything about this article is something you liked repeatedly".
"""

import math
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword
from api.domain.recommendation.models import (
    FilterMode,
    UserAuthorScore,
    UserCategoryScore,
    UserFeedScore,
    UserFilterRule,
    UserKeywordScore,
)

#: A boosted term is worth slightly less than a like, so an explicit rule tilts the ranking
#: without flattening what the votes have learned.
BOOST_WEIGHT = 1.0

#: Divisor inside tanh. At 3.0, two likes on a matching keyword already read ~75/100, and the
#: curve stays far from saturation for the first handful of votes.
_TANH_SCALE = 3.0


def to_relevance(raw: float) -> int:
    """Maps an unbounded average score to the 0-100 badge value, 50 being neutral."""
    return round(50 + 50 * math.tanh(raw / _TANH_SCALE))


async def score_articles(
    session: AsyncSession, user_id: UUID, articles: list[Article]
) -> dict[UUID, float]:
    """Raw average affinity per article id, boost rules included."""
    if not articles:
        return {}

    keywords_by_article, keyword_scores = await _load_keyword_scores(session, user_id, articles)
    feed_scores = await _load_feed_scores(
        session, user_id, {article.feed_id for article in articles}
    )
    author_scores = await _load_author_scores(
        session, user_id, {a.author_id for a in articles if a.author_id is not None}
    )
    category_scores = await _load_category_scores(
        session, user_id, {a.category_id for a in articles if a.category_id is not None}
    )
    boosted = await load_rule_terms(session, user_id, FilterMode.BOOST)

    return {
        article.id: _average_score(
            article,
            keywords_by_article,
            keyword_scores,
            feed_scores,
            author_scores,
            category_scores,
            boosted,
        )
        for article in articles
    }


async def load_rule_terms(session: AsyncSession, user_id: UUID, mode: FilterMode) -> list[str]:
    """The user's rule terms for one mode, lowercased."""
    terms = await session.scalars(
        select(UserFilterRule.term).where(
            UserFilterRule.user_id == user_id, UserFilterRule.mode == mode
        )
    )
    return [term.lower() for term in terms]


def matches_any_term(article: Article, terms: list[str]) -> bool:
    """Substring match over the title and the summary.

    The content is deliberately left out: it is stored HTML, so a term like `link` or `img` would
    match on markup rather than on what the article is about.
    """
    haystack = f"{article.title} {article.summary or ''}".lower()
    return any(term in haystack for term in terms)


def _average_score(
    article: Article,
    keywords_by_article: dict[UUID, list[UUID]],
    keyword_scores: dict[UUID, float],
    feed_scores: dict[UUID, float],
    author_scores: dict[UUID, float],
    category_scores: dict[UUID, float],
    boosted_terms: list[str],
) -> float:
    scores = [keyword_scores.get(kid, 0.0) for kid in keywords_by_article.get(article.id, [])]
    scores.append(feed_scores.get(article.feed_id, 0.0))
    if article.author_id is not None:
        scores.append(author_scores.get(article.author_id, 0.0))
    if article.category_id is not None:
        scores.append(category_scores.get(article.category_id, 0.0))
    average = sum(scores) / len(scores) if scores else 0.0
    if boosted_terms and matches_any_term(article, boosted_terms):
        average += BOOST_WEIGHT
    return average


async def _load_keyword_scores(
    session: AsyncSession, user_id: UUID, articles: list[Article]
) -> tuple[dict[UUID, list[UUID]], dict[UUID, float]]:
    rows = await session.execute(
        select(ArticleKeyword.article_id, ArticleKeyword.keyword_id).where(
            ArticleKeyword.article_id.in_([article.id for article in articles])
        )
    )
    keywords_by_article: dict[UUID, list[UUID]] = defaultdict(list)
    all_keyword_ids: set[UUID] = set()
    for article_id, keyword_id in rows:
        keywords_by_article[article_id].append(keyword_id)
        all_keyword_ids.add(keyword_id)

    if not all_keyword_ids:
        return keywords_by_article, {}

    scores = await session.scalars(
        select(UserKeywordScore).where(
            UserKeywordScore.user_id == user_id,
            UserKeywordScore.keyword_id.in_(all_keyword_ids),
        )
    )
    return keywords_by_article, {score.keyword_id: score.score for score in scores}


async def _load_feed_scores(
    session: AsyncSession, user_id: UUID, feed_ids: set[UUID]
) -> dict[UUID, float]:
    if not feed_ids:
        return {}
    rows = await session.scalars(
        select(UserFeedScore).where(
            UserFeedScore.user_id == user_id, UserFeedScore.feed_id.in_(feed_ids)
        )
    )
    return {row.feed_id: row.score for row in rows}


async def _load_author_scores(
    session: AsyncSession, user_id: UUID, author_ids: set[UUID]
) -> dict[UUID, float]:
    if not author_ids:
        return {}
    rows = await session.scalars(
        select(UserAuthorScore).where(
            UserAuthorScore.user_id == user_id, UserAuthorScore.author_id.in_(author_ids)
        )
    )
    return {row.author_id: row.score for row in rows}


async def _load_category_scores(
    session: AsyncSession, user_id: UUID, category_ids: set[UUID]
) -> dict[UUID, float]:
    if not category_ids:
        return {}
    rows = await session.scalars(
        select(UserCategoryScore).where(
            UserCategoryScore.user_id == user_id,
            UserCategoryScore.category_id.in_(category_ids),
        )
    )
    return {row.category_id: row.score for row in rows}
