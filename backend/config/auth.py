from functools import lru_cache

from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    magic_link_ttl_minutes: int = 15
    oidc_login_ttl_minutes: int = 10
    invitation_ttl_days: int = 7


@lru_cache
def get_auth_config() -> AuthConfig:
    return AuthConfig()
