from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class SourceType(StrEnum):
    MINIFLUX = "miniflux"
    # A page the user saved by URL, not something Miniflux polls: it has no real feed behind it,
    # so every user gets one synthetic MANUAL feed holding all of them.
    MANUAL = "manual"


class Folder(Base, TimestampMixin):
    __tablename__ = "folders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]


class Feed(Base, TimestampMixin):
    __tablename__ = "feeds"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    folder_id: Mapped[UUID | None] = mapped_column(ForeignKey("folders.id"), default=None)
    source_type: Mapped[SourceType]
    external_feed_id: Mapped[str]
    title: Mapped[str]
    url: Mapped[str]
