import asyncio
import logging

from sqlalchemy import CursorResult, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from config.miniflux import MinifluxConfig, get_miniflux_config

logger = logging.getLogger(__name__)

RETRY_INTERVAL_SECONDS = 3.0
MAX_ATTEMPTS = 100

_ENABLE_WEBHOOK = text(
    """
    update integrations
    set webhook_enabled = true, webhook_url = :url, webhook_secret = :secret
    where user_id = (select id from users where username = :username)
    """
)


async def enable_miniflux_webhook(database_url: str, config: MinifluxConfig) -> bool:
    """Points the Miniflux account's webhook at Lumia, signed with Lumia's own secret.

    Returns False while Miniflux has not created that account yet: its integrations row only
    exists once the account does.
    """
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            result: CursorResult[tuple[()]] = await connection.execute(
                _ENABLE_WEBHOOK,
                {
                    "username": config.miniflux_username,
                    "url": config.miniflux_webhook_url,
                    "secret": config.miniflux_webhook_secret,
                },
            )
    finally:
        await engine.dispose()
    return result.rowcount > 0


async def keep_enabling_miniflux_webhook(
    config: MinifluxConfig | None = None,
    *,
    retry_interval: float = RETRY_INTERVAL_SECONDS,
    max_attempts: int = MAX_ATTEMPTS,
) -> bool:
    """Retries while Miniflux is still migrating its schema or creating its admin account."""
    settings = config or get_miniflux_config()
    database_url = settings.miniflux_database_url
    if not database_url:
        return False
    for _ in range(max_attempts):
        try:
            if await enable_miniflux_webhook(database_url, settings):
                logger.info(
                    "enabled the Miniflux webhook towards %s", settings.miniflux_webhook_url
                )
                return True
        except (OSError, SQLAlchemyError):
            pass
        await asyncio.sleep(retry_interval)
    logger.warning(
        "could not enable the Miniflux webhook; new entries only arrive with the hourly "
        "reconciliation until it is turned on in the Miniflux Integrations page"
    )
    return False
