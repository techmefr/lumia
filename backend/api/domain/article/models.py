from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Computed, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.domain.feed.models import Feed
from api.technical.orm import Base, TimestampMixin


class Lang(StrEnum):
    FR = "fr"
    EN = "en"


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(unique=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(unique=True)


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("term", "lang", name="uq_keywords_term_lang"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    term: Mapped[str]
    lang: Mapped[Lang]


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    feed_id: Mapped[UUID] = mapped_column(ForeignKey("feeds.id"))
    author_id: Mapped[UUID | None] = mapped_column(ForeignKey("authors.id"), default=None)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), default=None)
    external_entry_id: Mapped[str]
    title: Mapped[str]
    url: Mapped[str]
    content: Mapped[str]
    summary: Mapped[str | None] = mapped_column(default=None)
    image_url: Mapped[str | None] = mapped_column(default=None)
    original_lang: Mapped[Lang] = mapped_column(default=Lang.FR)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Computed by postgres itself (see migration c2a6f81e934d for the generation expression, which
    # must stay in sync with this one), never written from python: a generated column rejects any
    # explicit value on insert or update.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "CASE original_lang "
            "WHEN 'EN' THEN to_tsvector('english', title || ' ' || coalesce(summary, '') "
            "|| ' ' || content) "
            "ELSE to_tsvector('french', title || ' ' || coalesce(summary, '') || ' ' || content) "
            "END",
            persisted=True,
        ),
    )

    author: Mapped[Author | None] = relationship(lazy="selectin")
    category: Mapped[Category | None] = relationship(lazy="selectin")
    feed: Mapped["Feed"] = relationship(lazy="selectin")
    keyword_links: Mapped[list["ArticleKeyword"]] = relationship(lazy="selectin", viewonly=True)


class ArticleKeyword(Base):
    __tablename__ = "article_keywords"

    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    keyword_id: Mapped[UUID] = mapped_column(ForeignKey("keywords.id"), primary_key=True)
    weight: Mapped[float]

    keyword: Mapped[Keyword] = relationship(lazy="selectin")
