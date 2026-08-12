from functools import lru_cache

from pydantic_settings import BaseSettings


class DeeplConfig(BaseSettings):
    deepl_api_key: str
    deepl_base_url: str = "https://api-free.deepl.com"


@lru_cache
def get_deepl_config() -> DeeplConfig:
    return DeeplConfig()
