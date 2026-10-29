from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, or_, select

from api.domain.article.models import Article
from api.domain.article.search_config import SEARCH_REGCONFIGS
from api.domain.recommendation.models import UserArticleFeedback


def exclude_muted_terms(query: Select[Article], terms: list[str]) -> Select[Article]:
    """Drops the articles a mute rule matches, in SQL.

    Same reach as `matches_any_term` — the title and the summary, never the stored HTML — but done
    here so the window and the offset apply to what the reader actually gets. `summary` is nullable
    and a comparison against NULL is NULL, not false, so it is coalesced before matching: otherwise
    every article without a summary would be filtered out by the negation.
    """
    patterns = [f"%{term}%" for term in terms]
    return query.where(
        ~or_(
            *[Article.title.ilike(pattern) for pattern in patterns],
            *[func.coalesce(Article.summary, "").ilike(pattern) for pattern in patterns],
        )
    )


def search_condition(q: str) -> ColumnElement[bool]:
    """Matches the generated `search_vector` column against the reader's search text.

    An article's vector is built under the configuration of its own `original_lang`, and a reader's
    library mixes languages, so a single query has to reach all of them: the query text is parsed
    under every configuration the index actually uses, and any match counts.

    The per-configuration queries are OR-ed together into one tsquery rather than compared with one
    `@@` each. Both forms return the same rows, but this one is a single operator against the GIN
    index instead of nine, which keeps widening the language coverage from costing nine index
    scans. Postgres tolerates a query text with nothing recognised under a given configuration
    (`websearch_to_tsquery` then returns an empty tsquery, which contributes nothing to the
    disjunction), so this never raises — it only narrows to whichever languages the terms parse as.
    """
    first, *rest = SEARCH_REGCONFIGS
    combined: ColumnElement[Any] = func.websearch_to_tsquery(first, q)
    for regconfig in rest:
        combined = combined.op("||")(func.websearch_to_tsquery(regconfig, q))
    return Article.search_vector.op("@@")(combined)


def apply_unread_only(query: Select[Article], user_id: UUID) -> Select[Article]:
    """Keeps articles with no read feedback row for this user — absence of a row means unread."""
    read_rows = select(UserArticleFeedback.article_id).where(
        UserArticleFeedback.user_id == user_id,
        UserArticleFeedback.article_id == Article.id,
        UserArticleFeedback.read.is_(True),
    )
    return query.where(~read_rows.exists())
