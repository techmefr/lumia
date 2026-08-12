import pytest
from pydantic import ValidationError

from config.redis import RedisConfig


def test_reads_redis_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://host:6379/2")
    config = RedisConfig()
    assert config.redis_url == "redis://host:6379/2"


def test_missing_redis_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValidationError):
        RedisConfig()
