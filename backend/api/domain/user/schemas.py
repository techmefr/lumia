from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from api.domain.user.models import (
    AIProvider,
    OrbitPosition,
    ReadingLang,
    Role,
    Theme,
    TranslationProvider,
)


class OnboardingAdminRequest(BaseModel):
    email: EmailStr
    username: str
    # The account created here has full instance-admin rights, so a short password is the one
    # place in the app that can't be left to the reader's own judgement.
    password: str = Field(min_length=8)
    # Left out, the two quotas fall back to what the environment says rather than to a literal
    # repeated on both sides of the wire.
    max_accounts: int | None = Field(default=None, ge=1)
    disk_quota_mb: int | None = Field(default=None, ge=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    token: str


class SsoCallbackRequest(BaseModel):
    code: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: UUID
    email: str
    username: str
    role: Role
    theme: Theme
    orbit_position: OrbitPosition
    font_base_size: int
    preferred_language: ReadingLang
    ai_provider: AIProvider | None
    ai_endpoint_url: str | None
    ai_model: str | None
    # The keys themselves are never returned, only whether one is on file: a settings form
    # needs to show "configurée" without ever putting the secret back on the wire.
    ai_api_key_set: bool
    translation_provider: TranslationProvider | None
    translation_api_key_set: bool


class MeUpdateRequest(BaseModel):
    theme: Theme | None = None
    orbit_position: OrbitPosition | None = None
    font_base_size: int | None = None
    preferred_language: ReadingLang | None = None
    ai_provider: AIProvider | None = None
    ai_api_key: str | None = None
    ai_endpoint_url: str | None = None
    ai_model: str | None = None
    translation_provider: TranslationProvider | None = None
    translation_api_key: str | None = None
