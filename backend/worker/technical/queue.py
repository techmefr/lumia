from collections.abc import Awaitable, Callable
from typing import Any, ClassVar

from arq.connections import RedisSettings

from config.redis import get_redis_config


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Awaitable[Any]]]] = []
    redis_settings = RedisSettings.from_dsn(get_redis_config().redis_url)
