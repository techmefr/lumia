from functools import lru_cache

from pydantic_settings import BaseSettings


class MinifluxConfig(BaseSettings):
    miniflux_base_url: str
    miniflux_username: str
    miniflux_password: str
    # No default: an instance that starts without one would silently accept unsigned webhooks
    # rather than refuse to boot, and that is the failure mode this field exists to rule out.
    miniflux_webhook_secret: str


@lru_cache
def get_miniflux_config() -> MinifluxConfig:
    return MinifluxConfig()
