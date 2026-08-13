from functools import lru_cache

from pydantic_settings import BaseSettings


class MinifluxConfig(BaseSettings):
    miniflux_base_url: str
    miniflux_username: str
    miniflux_password: str


@lru_cache
def get_miniflux_config() -> MinifluxConfig:
    return MinifluxConfig()
