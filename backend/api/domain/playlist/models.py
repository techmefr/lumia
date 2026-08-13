from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.domain.article.models import Article
from api.technical.orm import Base, TimestampMixin


class Playlist(Base, TimestampMixin):
    __tablename__ = "playlists"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]

    items: Mapped[list["PlaylistItem"]] = relationship(
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PlaylistItem.position",
        back_populates="playlist",
    )


class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    __table_args__ = (
        UniqueConstraint("playlist_id", "article_id", name="uq_playlist_items_playlist_article"),
    )

    playlist_id: Mapped[UUID] = mapped_column(ForeignKey("playlists.id"), primary_key=True)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    # Dense 0-based rank inside the playlist; reordering rewrites the whole run rather than
    # juggling gaps, which keeps "move up/down" trivial for lists this size.
    position: Mapped[int]

    playlist: Mapped[Playlist] = relationship(back_populates="items")
    article: Mapped[Article] = relationship(lazy="selectin")
