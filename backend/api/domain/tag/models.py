from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """A label the reader sticks on articles themselves.

    Not a `Keyword`: keywords are derived by the worker, shared across accounts and feed the
    relevance score, whereas a tag belongs to one reader and never weighs on any score. Tagging
    must not turn into a vote the reader did not mean to cast.
    """

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_tags_user_slug"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str]
    # The casefolded name, so "Cuisine" and "cuisine" cannot both exist for one reader.
    slug: Mapped[str]


class ArticleTag(Base):
    __tablename__ = "article_tags"

    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("tags.id"), primary_key=True, index=True)
