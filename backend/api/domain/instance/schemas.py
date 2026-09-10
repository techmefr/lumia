from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from api.domain.instance.models import AccessMode, AccessRequestStatus
from api.domain.user.models import Role


class InstanceSettingsResponse(BaseModel):
    max_accounts: int
    disk_quota_mb: int
    access_mode: AccessMode
    account_count: int


class InstanceSettingsUpdateRequest(BaseModel):
    max_accounts: int | None = Field(default=None, ge=1)
    disk_quota_mb: int | None = Field(default=None, ge=1)
    access_mode: AccessMode | None = None


class InstanceAccessModeResponse(BaseModel):
    """The only setting a visitor may read, so the sign-in screen knows what to offer."""

    access_mode: AccessMode


class AccountUsageResponse(BaseModel):
    id: UUID
    email: str
    username: str
    role: Role
    used_mb: int
    quota_mb: int


class AccessRequestCreateRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=80)


class AccessRequestResponse(BaseModel):
    id: UUID
    email: str
    username: str
    status: AccessRequestStatus
    created_at: datetime
    decided_at: datetime | None
