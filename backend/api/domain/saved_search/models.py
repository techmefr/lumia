from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class SavedSearch(Base, TimestampMixin):
    """A named, persisted set of search filters the reader can re-run with one click.

    The filter fields mirror `GET /articles` exactly (see `article/search_filters.py`): a saved
    search is that same query, given a name and a place to live, nothing more. `is_alert` promotes
    it to a keyword alert — the worker pipeline then checks every newly ingested article against it
    instead of leaving it as a view the reader has to open themselves.
    """

    __tablename__ = "saved_searches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    query: Mapped[str | None] = mapped_column(default=None)
    folder_id: Mapped[UUID | None] = mapped_column(ForeignKey("folders.id"), default=None)
    feed_id: Mapped[UUID | None] = mapped_column(ForeignKey("feeds.id"), default=None)
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("authors.id"), default=None)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), default=None)
    keyword_id: Mapped[UUID | None] = mapped_column(ForeignKey("keywords.id"), default=None)
    is_alert: Mapped[bool] = mapped_column(default=False)


class SavedSearchMatch(Base, TimestampMixin):
    """One article a keyword alert has already notified its owner about.

    This is the alert's watermark: a plain "last seen timestamp" column would break the moment two
    articles from different feeds land in the same tick with out-of-order `published_at` values,
    while a per-article row can never be double-sent regardless of ingestion order, and the unique
    constraint makes a retried ingestion job idempotent for free.
    """

    __tablename__ = "saved_search_matches"
    __table_args__ = (
        UniqueConstraint(
            "saved_search_id", "article_id", name="uq_saved_search_matches_search_article"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    saved_search_id: Mapped[UUID] = mapped_column(ForeignKey("saved_searches.id"))
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"))
