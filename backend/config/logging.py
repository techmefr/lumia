from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


class LoggingConfig(BaseSettings):
    log_level: str = "INFO"
    # JSON by default because the deployed instances are the ones nobody can attach a debugger
    # to; a developer running the stack locally sets LOG_FORMAT=console to get readable lines.
    log_format: LogFormat = LogFormat.JSON


@lru_cache
def get_logging_config() -> LoggingConfig:
    return LoggingConfig()
