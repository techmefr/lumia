from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

from config.auth import PLACEHOLDER_SECRETS


class MinifluxConfig(BaseSettings):
    miniflux_base_url: str
    miniflux_username: str
    miniflux_password: str
    # No default: an instance that starts without one would silently accept unsigned webhooks
    # rather than refuse to boot, and that is the failure mode this field exists to rule out.
    miniflux_webhook_secret: str

    @field_validator("miniflux_password")
    @classmethod
    def reject_placeholder_password(cls, value: str) -> str:
        if value.strip().lower() in PLACEHOLDER_SECRETS:
            raise ValueError("MINIFLUX_PASSWORD must be replaced with a generated password")
        return value

    @field_validator("miniflux_webhook_secret")
    @classmethod
    def reject_placeholder_webhook_secret(cls, value: str) -> str:
        if value.strip().lower() in PLACEHOLDER_SECRETS:
            raise ValueError("MINIFLUX_WEBHOOK_SECRET must be replaced with a generated secret")
        return value


@lru_cache
def get_miniflux_config() -> MinifluxConfig:
    return MinifluxConfig()
