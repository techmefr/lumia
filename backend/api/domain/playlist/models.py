from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.domain.article.models import Article
from api.technical.orm import Base, TimestampMixin


class MemberRole(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"


class PlaylistRole(StrEnum):
    """What an account can do on a playlist: the owner is not a membership row, so it lives here."""

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


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
    members: Mapped[list["PlaylistMember"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", back_populates="playlist"
    )


class PlaylistMember(Base, TimestampMixin):
    __tablename__ = "playlist_members"

    playlist_id: Mapped[UUID] = mapped_column(ForeignKey("playlists.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    role: Mapped[MemberRole]

    playlist: Mapped[Playlist] = relationship(back_populates="members")


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    playlist_id: Mapped[UUID] = mapped_column(ForeignKey("playlists.id"), primary_key=True)
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"), primary_key=True)
    # Dense 0-based rank inside the playlist; reordering rewrites the whole run rather than
    # juggling gaps, which keeps "move up/down" trivial for lists this size.
    position: Mapped[int]
    # Who put the article there. Null only for items from before playlists could be shared.
    added_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)

    playlist: Mapped[Playlist] = relationship(back_populates="items")
    article: Mapped[Article] = relationship(lazy="selectin")
