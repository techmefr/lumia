from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class AccessMode(StrEnum):
    """How a new account can come to exist on this instance."""

    CLOSED = "closed"
    ON_APPROVAL = "on_approval"
    OPEN = "open"


class AccessRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequest(Base, TimestampMixin):
    """A visitor asking for an account on an instance that runs on approval.

    The email is unique across requests rather than per status: letting the same address queue a
    second request would give a rejected visitor an unlimited retry loop through the admin's inbox.
    """

    __tablename__ = "access_requests"
    __table_args__ = (UniqueConstraint("email", name="uq_access_requests_email"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str]
    username: Mapped[str]
    status: Mapped[AccessRequestStatus] = mapped_column(default=AccessRequestStatus.PENDING)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    decided_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
