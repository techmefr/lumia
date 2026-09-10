import pytest
from pydantic import ValidationError

from config.logging import LogFormat, LoggingConfig


def test_defaults_to_json_at_info_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    config = LoggingConfig()
    assert config.log_level == "INFO"
    assert config.log_format is LogFormat.JSON


def test_reads_the_level_and_the_format_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "console")
    config = LoggingConfig()
    assert config.log_level == "DEBUG"
    assert config.log_format is LogFormat.CONSOLE


def test_rejects_an_unknown_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_FORMAT", "yaml")
    with pytest.raises(ValidationError):
        LoggingConfig()
