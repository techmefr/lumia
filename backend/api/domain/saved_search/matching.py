from sqlalchemy import Select, select

from api.domain.article.filters import exclude_muted_terms, search_condition
from api.domain.article.models import Article
from api.domain.feed.models import Feed
from api.domain.saved_search.models import SavedSearch


def articles_matching(search: SavedSearch, *, muted_terms: list[str]) -> Select[tuple[Article]]:
    """The reader's articles a saved search selects, built from the pieces `GET /articles` uses.

    Muted terms apply too: an alert on a topic the reader also muted would otherwise notify about
    articles the lists hide.
    """
    query = (
        select(Article)
        .join(Feed, Feed.id == Article.feed_id)
        .where(Feed.user_id == search.user_id, search_condition(search.query))
    )
    if search.feed_id is not None:
        query = query.where(Article.feed_id == search.feed_id)
    if search.folder_id is not None:
        query = query.where(Feed.folder_id == search.folder_id)
    if muted_terms:
        query = exclude_muted_terms(query, muted_terms)
    return query
