"""Content-based relatedness between a user's own articles.

No LLM call: the enrichment pipeline already extracts weighted keywords per article (TF-IDF, see
`worker.domain.extraction.tfidf`), and shared keywords are a strong, free relatedness signal on
their own. Combined with same feed/author/category and publication proximity, this gets to "related
articles" without the latency or cost of a paid API call on or off the request path.

Computed once per new article rather than at every article page view, per the candidate pool a
keyword join already narrows to. The candidates a new article scores against are refreshed too, so
an older article gains a fresh neighbour without rescanning the whole library.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.domain.article.models import Article, ArticleKeyword
from api.domain.feed.models import Feed
from api.domain.recommendation.models import RelatedArticle

#: How many neighbours are kept per article. Wider than what a reader ever sees, so the serving
#: side still has choices left after already-read articles are filtered out.
_STORED_CANDIDATES = 10

#: How many of an article's own stored neighbours are, in turn, refreshed when it is created. Keeps
#: older articles aware of a new arrival without rescanning the whole library.
_REFRESH_FANOUT = 10

_SAME_FEED_BONUS = 1.0
_SAME_AUTHOR_BONUS = 1.0
_SAME_CATEGORY_BONUS = 0.5

#: A pair published within a day of each other gets close to the full bonus; a month apart, almost
#: none. Chosen so recency nudges the ranking without ever dominating a strong keyword overlap.
_RECENCY_HALF_LIFE_DAYS = 5.0
_RECENCY_BONUS = 1.0


async def refresh_related_articles(session: AsyncSession, article: Article, user_id: UUID) -> None:
    """(Re)computes `article`'s related set, then refreshes the neighbours it just picked.

    Only the candidates this article actually scored against are refreshed: each one might now
    have a better neighbour than it did before this article existed, but nothing else in the
    library could have changed. `user_id` is passed explicitly rather than read off
    `article.feed.user_id`, since `article` may be a freshly created, not-yet-refreshed instance.
    """
    scored = await _score_candidates(session, article, user_id)
    await _store(session, article.id, scored[:_STORED_CANDIDATES])

    for candidate_id, _score in scored[:_REFRESH_FANOUT]:
        candidate = await session.get(Article, candidate_id)
        if candidate is not None:
            neighbour_scores = await _score_candidates(session, candidate, user_id)
            await _store(session, candidate.id, neighbour_scores[:_STORED_CANDIDATES])


async def fetch_related(
    session: AsyncSession, user_id: UUID, article_id: UUID, *, limit: int
) -> list[Article]:
    """The stored neighbours of one article, still owned by `user_id`, best score first."""
    rows = await session.execute(
        select(Article)
        .join(RelatedArticle, RelatedArticle.related_article_id == Article.id)
        .join(Feed, Feed.id == Article.feed_id)
        .where(
            RelatedArticle.article_id == article_id,
            Feed.user_id == user_id,
        )
        .order_by(RelatedArticle.score.desc())
        .limit(limit)
    )
    return list(rows.scalars())


async def _score_candidates(
    session: AsyncSession, article: Article, user_id: UUID
) -> list[tuple[UUID, float]]:
    other = aliased(ArticleKeyword)
    candidate_article = aliased(Article)
    keyword_rows = await session.execute(
        select(other.article_id, ArticleKeyword.weight, other.weight)
        .join(other, other.keyword_id == ArticleKeyword.keyword_id)
        .join(candidate_article, candidate_article.id == other.article_id)
        .join(Feed, Feed.id == candidate_article.feed_id)
        .where(
            ArticleKeyword.article_id == article.id,
            other.article_id != article.id,
            Feed.user_id == user_id,
        )
    )
    keyword_score: dict[UUID, float] = {}
    for candidate_id, own_weight, other_weight in keyword_rows:
        keyword_score[candidate_id] = keyword_score.get(candidate_id, 0.0) + min(
            own_weight, other_weight
        )
    if not keyword_score:
        return []

    candidates = await session.scalars(
        select(Article).where(Article.id.in_(keyword_score.keys()))
    )
    scored = [
        (candidate.id, keyword_score[candidate.id] + _bonus_score(article, candidate))
        for candidate in candidates
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def _bonus_score(article: Article, candidate: Article) -> float:
    bonus = 0.0
    if candidate.feed_id == article.feed_id:
        bonus += _SAME_FEED_BONUS
    if article.author_id is not None and candidate.author_id == article.author_id:
        bonus += _SAME_AUTHOR_BONUS
    if article.category_id is not None and candidate.category_id == article.category_id:
        bonus += _SAME_CATEGORY_BONUS
    days_apart = abs((candidate.published_at - article.published_at).total_seconds()) / 86400
    bonus += _RECENCY_BONUS * (0.5 ** (days_apart / _RECENCY_HALF_LIFE_DAYS))
    return bonus


async def _store(session: AsyncSession, article_id: UUID, scored: Sequence[tuple[UUID, float]]) -> None:
    await session.execute(delete(RelatedArticle).where(RelatedArticle.article_id == article_id))
    for related_article_id, score in scored:
        session.add(
            RelatedArticle(article_id=article_id, related_article_id=related_article_id, score=score)
        )
    await session.flush()
