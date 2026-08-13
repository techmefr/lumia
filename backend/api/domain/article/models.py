from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

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


class ArticleKeyword(Base):
    __tablename__ = "article_keywords"

    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    keyword_id: Mapped[UUID] = mapped_column(ForeignKey("keywords.id"), primary_key=True)
    weight: Mapped[float]
