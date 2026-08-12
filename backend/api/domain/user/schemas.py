from uuid import UUID

from pydantic import BaseModel, EmailStr

from api.domain.user.models import AIProvider, OrbitPosition, Role, Theme


class OnboardingAdminRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
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
    ai_provider: AIProvider | None
    ai_endpoint_url: str | None
    ai_api_key_set: bool


class MeUpdateRequest(BaseModel):
    theme: Theme | None = None
    orbit_position: OrbitPosition | None = None
    font_base_size: int | None = None
    ai_provider: AIProvider | None = None
    ai_api_key: str | None = None
    ai_endpoint_url: str | None = None
