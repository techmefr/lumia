from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class FeverKey(Base, TimestampMixin):
    """The credential a third-party reader app syncs with, one per reader.

    The protocol makes the client send md5(email:password), so a client cannot be given anything
    but a password-shaped secret. Lumia never stores the reader's own password for that: it draws a
    separate secret, shows it once, and keeps only the sha256 of the key the client will derive
    from it. A leaked row cannot be replayed as the reader's login, and revoking deletes the row.
    """

    __tablename__ = "fever_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    key_hash: Mapped[str] = mapped_column(unique=True)
