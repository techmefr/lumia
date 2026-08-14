from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class Vote(StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"


class FilterMode(StrEnum):
    BOOST = "boost"
    MUTE = "mute"


class UserFilterRule(Base, TimestampMixin):
    """An explicit rule on top of what the votes have learned.

    A boosted term lifts an article's relevance; a muted term removes it from the lists and from
    L'Étincelle entirely. Terms are stored lowercased so the uniqueness constraint means what it
    looks like.
    """

    __tablename__ = "user_filter_rules"
    __table_args__ = (
        UniqueConstraint("user_id", "term", "mode", name="uq_user_filter_rules_user_term_mode"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    term: Mapped[str]
    mode: Mapped[FilterMode]


class UserArticleFeedback(Base, TimestampMixin):
    __tablename__ = "user_article_feedback"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    sentiment: Mapped[Vote | None] = mapped_column(default=None)
    saved: Mapped[bool] = mapped_column(default=False)
    favorite: Mapped[bool] = mapped_column(default=False)
    read: Mapped[bool] = mapped_column(default=False)
    # How far down the article the user got, 0.0 to 1.0. Persisted so reopening an article on
    # another device resumes where the reading stopped.
    scroll_progress: Mapped[float] = mapped_column(default=0.0)


class UserKeywordScore(Base):
    __tablename__ = "user_keyword_scores"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    keyword_id: Mapped[UUID] = mapped_column(ForeignKey("keywords.id"), primary_key=True)
    score: Mapped[float] = mapped_column(default=0.0)


class UserFeedScore(Base):
    __tablename__ = "user_feed_scores"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    feed_id: Mapped[UUID] = mapped_column(ForeignKey("feeds.id"), primary_key=True)
    score: Mapped[float] = mapped_column(default=0.0)


class UserAuthorScore(Base):
    __tablename__ = "user_author_scores"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("authors.id"), primary_key=True)
    score: Mapped[float] = mapped_column(default=0.0)


class UserCategoryScore(Base):
    __tablename__ = "user_category_scores"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), primary_key=True)
    score: Mapped[float] = mapped_column(default=0.0)
