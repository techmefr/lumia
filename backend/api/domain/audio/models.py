from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class ArticleAudio(Base, TimestampMixin):
    """A synthesised reading, kept so an article is only ever paid for once per voice.

    Per account because the audio was bought with that account's own key and endpoint: two readers
    who configured different servers must never be served each other's file.
    """

    __tablename__ = "article_audios"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", "voice_hash", name="uq_article_audios_voice"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), index=True)
    voice_hash: Mapped[str]
    content_type: Mapped[str]
    size_bytes: Mapped[int]
    data: Mapped[bytes] = mapped_column(LargeBinary)
