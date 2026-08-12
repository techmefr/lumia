from functools import lru_cache

from pydantic_settings import BaseSettings


class CryptoConfig(BaseSettings):
    secret_encryption_key: str


@lru_cache
def get_crypto_config() -> CryptoConfig:
    return CryptoConfig()
