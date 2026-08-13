from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class Vote(StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"


class UserArticleFeedback(Base, TimestampMixin):
    __tablename__ = "user_article_feedback"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    sentiment: Mapped[Vote | None] = mapped_column(default=None)
    saved: Mapped[bool] = mapped_column(default=False)
    favorite: Mapped[bool] = mapped_column(default=False)
    read: Mapped[bool] = mapped_column(default=False)


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
