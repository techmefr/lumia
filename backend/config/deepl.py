from functools import lru_cache

from pydantic_settings import BaseSettings


class DeeplConfig(BaseSettings):
    # Optional: an install can translate through the account's own LLM instead, or not at all.
    deepl_api_key: str | None = None
    deepl_base_url: str = "https://api-free.deepl.com"


@lru_cache
def get_deepl_config() -> DeeplConfig:
    return DeeplConfig()
