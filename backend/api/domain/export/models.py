from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class ExportKind(StrEnum):
    PLAYLIST_EPUB = "playlist_epub"


class ExportStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class ExportJob(Base, TimestampMixin):
    """A file the worker builds for a reader and keeps just long enough to be downloaded.

    The bytes live in the row: the instance has no object store, and a database that already holds
    the reader's articles can hold a book made of them for a day. `expires_at` is what keeps that
    from becoming a second copy of everything: the purge deletes the row, file included.
    """

    __tablename__ = "export_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[ExportKind]
    subject_id: Mapped[UUID]
    status: Mapped[ExportStatus] = mapped_column(default=ExportStatus.PENDING)
    file_name: Mapped[str | None] = mapped_column(default=None)
    data: Mapped[bytes | None] = mapped_column(LargeBinary, default=None, deferred=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
