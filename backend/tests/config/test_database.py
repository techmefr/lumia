import pytest
from pydantic import ValidationError

from config.database import DatabaseConfig, get_engine


def test_reads_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pw@host/db")
    config = DatabaseConfig()
    assert config.database_url == "postgresql+asyncpg://user:pw@host/db"


def test_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        DatabaseConfig()


def test_get_engine_uses_asyncpg_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pw@host/db")
    get_engine.cache_clear()
    engine = get_engine()
    assert engine.url.drivername == "postgresql+asyncpg"
