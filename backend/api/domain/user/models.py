from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.domain.instance.models import AccessMode
from api.technical.orm import Base, TimestampMixin


class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class AIProvider(StrEnum):
    MISTRAL = "mistral"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMMA = "gemma"
    CUSTOM = "custom"


class TranslationProvider(StrEnum):
    DEEPL = "deepl"


class ReadingLang(StrEnum):
    """The language the reader wants articles in.

    Deliberately not `Lang`: that one is the language an article was written in. The two sets of
    values happen to line up now, but they answer different questions (what a text is written in
    versus what a reader asked for), and a stemmer covering one of them is incidental, not
    something either type should be defined in terms of.
    """

    FR = "fr"
    EN = "en"
    ES = "es"
    DE = "de"
    IT = "it"
    PT = "pt"
    RU = "ru"
    AR = "ar"
    ZH = "zh"
    MG = "mg"


class MagicLinkPurpose(StrEnum):
    """What the reader asked the link for, which decides where in the app it lands them.

    The token itself is the same either way: both purposes prove the same thing, control of the
    mailbox, and a reader who can sign in can already set a new password from the settings.
    """

    SIGN_IN = "sign_in"
    PASSWORD_RESET = "password_reset"


class DigestFrequency(StrEnum):
    """How often the reader asked for a digest, `NEVER` being the only default we may assume.

    Opting in is the reader's act: an instance that mailed everyone by default would be sending
    to addresses that were given for signing in, not for being written to.
    """

    NEVER = "never"
    DAILY = "daily"
    WEEKLY = "weekly"


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
    # Per account, not for the whole instance: what it caps is how much one reader may store.
    disk_quota_mb: Mapped[int]
    access_mode: Mapped[AccessMode] = mapped_column(default=AccessMode.CLOSED)
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
    preferred_language: Mapped[ReadingLang] = mapped_column(default=ReadingLang.FR)
    digest_frequency: Mapped[DigestFrequency] = mapped_column(default=DigestFrequency.NEVER)
    #: Hour of the day, read in `digest_timezone`: "the morning digest" means the reader's morning,
    #: and a fixed UTC hour is somebody's middle of the night nearly everywhere.
    digest_hour: Mapped[int] = mapped_column(default=8)
    digest_timezone: Mapped[str] = mapped_column(default="UTC")
    #: The period the last digest covered, "2026-09-16" or "2026-W38". Comparing the current period
    #: against it is what makes a send idempotent: a worker restart re-enters the same period and
    #: finds it already spent, where a "sent in the last 24 hours" check drifts by an hour a day.
    digest_last_period: Mapped[str | None] = mapped_column(default=None)
    digest_last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    #: Set as soon as enrolment starts, so the confirmation step has something to check against.
    #: On its own it means nothing: only `totp_confirmed_at` turns the second factor on.
    totp_secret_encrypted: Mapped[str | None] = mapped_column(default=None)
    #: When the reader proved their authenticator produces the right codes. Until then the secret
    #: is a draft, and a misconfigured app would otherwise lock the account out for good.
    totp_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    #: The last time step accepted for this account. A code stays valid for its whole window, so
    #: without this an overheard code can be replayed until the window turns.
    totp_last_used_step: Mapped[int | None] = mapped_column(BigInteger, default=None)


class RecoveryCode(Base, TimestampMixin):
    """One of the codes handed out at enrolment, the way back in when the authenticator is gone.

    Stored hashed like every other credential in this schema, and spent rather than deleted: a
    used code has to stay unusable, and a listing that shrinks tells nobody why.
    """

    __tablename__ = "recovery_codes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(unique=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    #: Every rotation of one login shares a family, so a replayed token can revoke its siblings
    #: without touching the sessions the reader has on other devices.
    family_id: Mapped[UUID] = mapped_column(default=uuid4, index=True)
    #: Set when the token is rotated away or logged out. Kept rather than deleted: a token that
    #: comes back after being revoked is the signal that it was stolen.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Invitation(Base, TimestampMixin):
    """An admin's promise of a seat, redeemable once.

    The invited address is fixed at invitation time: the token is a proof that the admin meant to
    let *that* person in, not a general-purpose sign-up voucher.
    """

    __tablename__ = "invitations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instance_id: Mapped[UUID] = mapped_column(ForeignKey("instances.id"))
    email: Mapped[str]
    role: Mapped[Role] = mapped_column(default=Role.MEMBER)
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class OidcLoginAttempt(Base, TimestampMixin):
    """One SSO login in flight, so the callback can prove it answers a login we started."""

    __tablename__ = "oidc_login_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    state: Mapped[str] = mapped_column(unique=True)
    # The nonce is kept in clear, unlike the state: it is not a credential anyone can present, it
    # is compared against a claim inside a token the provider had to sign.
    nonce: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class MagicLinkToken(Base, TimestampMixin):
    __tablename__ = "magic_link_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
