from functools import lru_cache

from pydantic_settings import BaseSettings


class EmailConfig(BaseSettings):
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from_address: str
    smtp_use_tls: bool = True
    # Only used to turn the magic-link token into a clickable url in the email body. Defaults to
    # the docker-compose default so a fresh self-host works out of the box; a real deployment
    # reachable under its own domain or a LAN address should override it.
    frontend_url: str = "http://localhost:8080"


@lru_cache
def get_email_config() -> EmailConfig:
    return EmailConfig()
