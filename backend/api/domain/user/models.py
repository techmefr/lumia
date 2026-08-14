from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.domain.article.models import Lang
from api.technical.orm import Base, TimestampMixin


class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class AIProvider(StrEnum):
    MISTRAL = "mistral"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class TranslationProvider(StrEnum):
    DEEPL = "deepl"


class Theme(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class OrbitPosition(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class Instance(Base, TimestampMixin):
    __tablename__ = "instances"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    max_accounts: Mapped[int]
    disk_quota_mb: Mapped[int]
    oidc_issuer: Mapped[str | None] = mapped_column(default=None)
    oidc_client_id: Mapped[str | None] = mapped_column(default=None)
    oidc_client_secret_encrypted: Mapped[str | None] = mapped_column(default=None)
    oidc_redirect_uri: Mapped[str | None] = mapped_column(default=None)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instance_id: Mapped[UUID] = mapped_column(ForeignKey("instances.id"))
    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str]
    password_hash: Mapped[str | None] = mapped_column(default=None)
    sso_subject: Mapped[str | None] = mapped_column(unique=True, default=None)
    role: Mapped[Role] = mapped_column(default=Role.MEMBER)
    ai_provider: Mapped[AIProvider | None] = mapped_column(default=None)
    ai_api_key_encrypted: Mapped[str | None] = mapped_column(default=None)
    ai_endpoint_url: Mapped[str | None] = mapped_column(default=None)
    ai_model: Mapped[str | None] = mapped_column(default=None)
    # Per account rather than per instance: the key is the user's, and so is the bill.
    translation_provider: Mapped[TranslationProvider | None] = mapped_column(default=None)
    translation_api_key_encrypted: Mapped[str | None] = mapped_column(default=None)
    theme: Mapped[Theme] = mapped_column(default=Theme.SYSTEM)
    orbit_position: Mapped[OrbitPosition] = mapped_column(default=OrbitPosition.RIGHT)
    font_base_size: Mapped[int] = mapped_column(default=16)
    preferred_language: Mapped[Lang] = mapped_column(default=Lang.FR)


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MagicLinkToken(Base, TimestampMixin):
    __tablename__ = "magic_link_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
