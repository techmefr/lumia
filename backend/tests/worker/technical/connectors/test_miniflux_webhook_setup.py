import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from config.miniflux import MinifluxConfig
from worker.technical.connectors.miniflux_webhook_setup import (
    enable_miniflux_webhook,
    keep_enabling_miniflux_webhook,
)

_MINIFLUX_SCHEMA = [
    "create table users (id bigserial primary key, username text not null unique)",
    """
    create table integrations (
        user_id int not null unique references users (id),
        webhook_enabled bool default 'f',
        webhook_url text default '',
        webhook_secret text default ''
    )
    """,
]


def _database_url(database: str) -> str:
    url = make_url(os.environ["DATABASE_URL"]).set(database=database)
    return url.render_as_string(hide_password=False)


async def _run(database_url: str, statement: str, params: dict[str, Any] | None = None) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(statement), params or {})
    finally:
        await engine.dispose()


@pytest.fixture
async def miniflux_database_url() -> AsyncIterator[str]:
    name = f"{make_url(os.environ['DATABASE_URL']).database}_miniflux"
    server = _database_url("postgres")
    await _run(server, f'drop database if exists "{name}"')
    await _run(server, f'create database "{name}"')
    url = _database_url(name)
    try:
        for statement in _MINIFLUX_SCHEMA:
            await _run(url, statement)
        yield url
    finally:
        await _run(server, f'drop database if exists "{name}"')


def _config(database_url: str | None) -> MinifluxConfig:
    return MinifluxConfig(
        miniflux_base_url="http://miniflux.test",
        miniflux_username="admin",
        miniflux_password="test-miniflux-password",
        miniflux_webhook_secret="test-miniflux-webhook-secret",
        miniflux_database_url=database_url,
        miniflux_webhook_url="http://lumia-backend-api:8000/webhooks/miniflux",
    )


async def _create_account(database_url: str, username: str) -> None:
    await _run(
        database_url, "insert into users (username) values (:username)", {"username": username}
    )
    await _run(
        database_url,
        "insert into integrations (user_id) select id from users where username = :username",
        {"username": username},
    )


async def _webhook_of(database_url: str, username: str) -> tuple[bool, str, str]:
    engine = create_async_engine(database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "select webhook_enabled, webhook_url, webhook_secret from integrations "
                        "join users on users.id = integrations.user_id where username = :username"
                    ),
                    {"username": username},
                )
            ).one()
    finally:
        await engine.dispose()
    return row[0], row[1], row[2]


async def test_the_webhook_points_at_lumia_with_its_own_secret(
    miniflux_database_url: str,
) -> None:
    await _create_account(miniflux_database_url, "admin")

    assert await enable_miniflux_webhook(miniflux_database_url, _config(miniflux_database_url))

    assert await _webhook_of(miniflux_database_url, "admin") == (
        True,
        "http://lumia-backend-api:8000/webhooks/miniflux",
        "test-miniflux-webhook-secret",
    )


async def test_other_miniflux_accounts_are_left_alone(miniflux_database_url: str) -> None:
    await _create_account(miniflux_database_url, "admin")
    await _create_account(miniflux_database_url, "someone-else")

    await enable_miniflux_webhook(miniflux_database_url, _config(miniflux_database_url))

    assert await _webhook_of(miniflux_database_url, "someone-else") == (False, "", "")


async def test_nothing_is_enabled_before_miniflux_creates_the_account(
    miniflux_database_url: str,
) -> None:
    config = _config(miniflux_database_url)

    assert not await enable_miniflux_webhook(miniflux_database_url, config)


async def test_retries_until_miniflux_has_created_the_account(
    miniflux_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def create_the_account_while_waiting(_delay: float) -> None:
        await _create_account(miniflux_database_url, "admin")

    monkeypatch.setattr(
        "worker.technical.connectors.miniflux_webhook_setup.asyncio.sleep",
        create_the_account_while_waiting,
    )

    assert await keep_enabling_miniflux_webhook(_config(miniflux_database_url), max_attempts=2)
    assert (await _webhook_of(miniflux_database_url, "admin"))[0] is True


async def test_gives_up_on_an_unreachable_miniflux_database() -> None:
    unreachable = "postgresql+asyncpg://miniflux:wrong@127.0.0.1:1/miniflux"

    assert not await keep_enabling_miniflux_webhook(
        _config(unreachable), retry_interval=0, max_attempts=2
    )


async def test_an_external_miniflux_is_never_touched() -> None:
    assert not await keep_enabling_miniflux_webhook(_config(None), retry_interval=0)
