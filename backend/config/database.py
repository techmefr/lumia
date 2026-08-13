from functools import lru_cache

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class DatabaseConfig(BaseSettings):
    database_url: str


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(DatabaseConfig().database_url)
