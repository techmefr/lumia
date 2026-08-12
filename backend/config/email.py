from functools import lru_cache

from pydantic_settings import BaseSettings


class EmailConfig(BaseSettings):
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from_address: str
    smtp_use_tls: bool = True


@lru_cache
def get_email_config() -> EmailConfig:
    return EmailConfig()
