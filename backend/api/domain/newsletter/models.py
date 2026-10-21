from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class NewsletterInbox(Base, TimestampMixin):
    """The secret address a reader hands to the service that forwards their newsletters.

    Only the hash of the token is stored, like every other opaque token here: the address is shown
    once, and a database leak does not hand out working inboxes. One inbox per reader, and
    revoking deletes the row, so a retired address cannot resolve in any state.
    """

    __tablename__ = "newsletter_inboxes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    token_hash: Mapped[str] = mapped_column(unique=True)
