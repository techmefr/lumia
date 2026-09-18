from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class FeverApiKey(Base, TimestampMixin):
    """The credential a Fever-speaking client sends as its `api_key` form field.

    Fever's own spec derives the key as md5(email:password), which Lumia cannot reproduce since
    passwords are argon2-hashed, not stored in a form md5 could be computed against. Instead this
    stores the exact digest a client will send once a token is minted for it: md5(email:token),
    computed once at issuance from the account's email and a freshly generated opaque token. Only
    that digest is kept, never the token or the password, so this is a comparison value rather than
    a reversible secret.
    """

    __tablename__ = "fever_api_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    digest: Mapped[str] = mapped_column(unique=True)
