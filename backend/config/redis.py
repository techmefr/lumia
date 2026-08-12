from functools import lru_cache

from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    redis_url: str


@lru_cache
def get_redis_config() -> RedisConfig:
    return RedisConfig()
