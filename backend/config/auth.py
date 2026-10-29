from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

PLACEHOLDER_SECRETS = frozenset({"change-me", "changeme", ""})


class AuthConfig(BaseSettings):
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    magic_link_ttl_minutes: int = 15
    oidc_login_ttl_minutes: int = 10
    invitation_ttl_days: int = 7

    @field_validator("jwt_secret")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        if value.strip().lower() in PLACEHOLDER_SECRETS:
            raise ValueError("JWT_SECRET must be replaced with a generated secret")
        return value


@lru_cache
def get_auth_config() -> AuthConfig:
    return AuthConfig()
