from datetime import datetime
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, EmailStr, Field, field_validator

from api.domain.feed.models import SourceType
from api.domain.recommendation.models import FilterMode
from api.domain.user.models import (
    AIProvider,
    DigestFrequency,
    MagicLinkPurpose,
    OrbitPosition,
    ReadingLang,
    Role,
    Theme,
    TranslationProvider,
)

# Every path that writes a password holds to the same floor: onboarding, an accepted invitation,
# a change from the settings and a reset from a magic link. A route that asked for less would be
# the one an attacker picks.
MIN_PASSWORD_LENGTH = 8


class OnboardingAdminRequest(BaseModel):
    email: EmailStr
    username: str
    # The account created here has full instance-admin rights, so a short password is the one
    # place in the app that can't be left to the reader's own judgement.
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)
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
    purpose: MagicLinkPurpose = MagicLinkPurpose.SIGN_IN


class MagicLinkVerifyRequest(BaseModel):
    token: str


class PasswordChangeRequest(BaseModel):
    """The current password is optional only for an account that has none to give yet."""

    current_password: str | None = None
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class SsoCallbackRequest(BaseModel):
    code: str
    state: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class InvitationRequest(BaseModel):
    email: EmailStr
    role: Role = Role.MEMBER


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    role: Role
    expires_at: datetime
    # The raw token is never returned: it only ever exists in the invitee's mailbox, so a leaked
    # admin listing cannot be redeemed.


class InvitationAcceptRequest(BaseModel):
    token: str
    username: str = Field(min_length=1)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)


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
    # Whether a password can be changed or has yet to be set: an account that only ever came in
    # through SSO or a magic link has none, and asking it for the current one would trap it.
    password_set: bool
    theme: Theme
    orbit_position: OrbitPosition
    font_base_size: int
    preferred_language: ReadingLang
    digest_frequency: DigestFrequency
    digest_hour: int
    digest_timezone: str
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
    digest_frequency: DigestFrequency | None = None
    # Bounded here rather than trusted from the form: an out-of-range hour would simply never
    # match and the reader would be left waiting for a mail that cannot come.
    digest_hour: int | None = Field(default=None, ge=0, le=23)
    digest_timezone: str | None = None
    ai_provider: AIProvider | None = None
    ai_api_key: str | None = None
    ai_endpoint_url: str | None = None
    ai_model: str | None = None
    translation_provider: TranslationProvider | None = None
    translation_api_key: str | None = None

    @field_validator("digest_timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        """Rejects a zone the server cannot resolve, rather than storing a name that never fires."""
        if value is not None and value not in available_timezones():
            raise ValueError("unknown timezone")
        return value
