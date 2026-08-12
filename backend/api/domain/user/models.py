from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.technical.orm import Base, TimestampMixin


class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class AIProvider(StrEnum):
    MISTRAL = "mistral"
    OPENAI = "openai"
    CUSTOM = "custom"


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


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instance_id: Mapped[UUID] = mapped_column(ForeignKey("instances.id"))
    email: Mapped[str] = mapped_column(unique=True)
    username: Mapped[str]
    password_hash: Mapped[str]
    role: Mapped[Role] = mapped_column(default=Role.MEMBER)
    ai_provider: Mapped[AIProvider | None] = mapped_column(default=None)
    ai_api_key_encrypted: Mapped[str | None] = mapped_column(default=None)
    ai_endpoint_url: Mapped[str | None] = mapped_column(default=None)
    theme: Mapped[Theme] = mapped_column(default=Theme.SYSTEM)
    orbit_position: Mapped[OrbitPosition] = mapped_column(default=OrbitPosition.RIGHT)
    font_base_size: Mapped[int] = mapped_column(default=16)


class UserSession(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime]
