from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from api.domain.feed.models import SourceType
from api.domain.recommendation.models import FilterMode
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
    max_accounts: int = 10
    disk_quota_mb: int = 1000


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


class DeleteAccountRequest(BaseModel):
    """Deleting is final and unattended, so it asks for more than a click.

    The address rules out a misdirected request; the password proves it is the account holder and
    not somebody who walked up to an unlocked screen. An account signed in through SSO or a magic
    link has no password to give, and the address is then all there is to ask for.
    """

    confirm_email: EmailStr
    password: str | None = None


class ExportedAccount(BaseModel):
    email: str
    username: str
    role: Role
    theme: Theme
    preferred_language: ReadingLang
    font_base_size: int
    created_at: datetime


class ExportedFeed(BaseModel):
    title: str
    url: str
    source_type: SourceType
    folder: str | None


class ExportedFilterRule(BaseModel):
    term: str
    mode: FilterMode


class ExportedArticle(BaseModel):
    title: str
    url: str
    published_at: datetime
    source: str


class ExportedPlaylist(BaseModel):
    name: str
    articles: list[ExportedArticle]


class AccountExportResponse(BaseModel):
    account: ExportedAccount
    feeds: list[ExportedFeed]
    filter_rules: list[ExportedFilterRule]
    playlists: list[ExportedPlaylist]
    saved: list[ExportedArticle]
    favorites: list[ExportedArticle]


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
