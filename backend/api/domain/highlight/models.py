from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.domain.article.models import Article
from api.technical.orm import Base, TimestampMixin


class Highlight(Base, TimestampMixin):
    """A passage a reader marked in an article, with the note they attached to it.

    The anchor is the passage itself (`quote`) plus a little text around it and its offset in the
    article's flattened text, never a DOM path: the content can be extracted or sanitised again and
    the markup shifts, while the text survives. The client uses the offsets as a hint and falls back
    on the quote and its context to find the passage again.
    """

    __tablename__ = "highlights"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), index=True)
    quote: Mapped[str] = mapped_column(Text)
    prefix: Mapped[str] = mapped_column(Text, default="")
    suffix: Mapped[str] = mapped_column(Text, default="")
    start_offset: Mapped[int]
    end_offset: Mapped[int]
    note: Mapped[str | None] = mapped_column(Text, default=None)

    article: Mapped[Article] = relationship(lazy="selectin")
