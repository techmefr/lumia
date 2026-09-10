import json
import logging
import sys
from collections.abc import Iterator

import pytest

from api.technical.logging.correlation import (
    reset_correlation_id,
    set_correlation_id,
)
from api.technical.logging.setup import (
    CorrelationIdFilter,
    JsonFormatter,
    build_handler,
    configure_logging,
)
from config.logging import get_logging_config


@pytest.fixture(autouse=True)
def _restore_root_logging() -> Iterator[None]:
    root_logger = logging.getLogger()
    handlers = list(root_logger.handlers)
    level = root_logger.level
    get_logging_config.cache_clear()
    yield
    root_logger.handlers = handlers
    root_logger.setLevel(level)
    get_logging_config.cache_clear()


def _format(record: logging.LogRecord) -> dict[str, object]:
    CorrelationIdFilter().filter(record)
    formatted: dict[str, object] = json.loads(JsonFormatter().format(record))
    return formatted


def _record() -> logging.LogRecord:
    return logging.LogRecord(
        name="lumia.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="something %s",
        args=("happened",),
        exc_info=None,
    )


def test_json_line_carries_the_level_logger_and_interpolated_message() -> None:
    payload = _format(_record())
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "lumia.test"
    assert payload["message"] == "something happened"
    assert payload["timestamp"]


def test_json_line_carries_the_extra_fields() -> None:
    record = _record()
    record.service = "deepl"
    record.status_code = 456
    payload = _format(record)
    assert payload["service"] == "deepl"
    assert payload["status_code"] == 456


def test_json_line_carries_the_current_correlation_id() -> None:
    token = set_correlation_id("job-7")
    try:
        payload = _format(_record())
    finally:
        reset_correlation_id(token)
    assert payload["correlation_id"] == "job-7"


def test_json_line_carries_no_correlation_id_outside_a_request_or_a_job() -> None:
    assert _format(_record())["correlation_id"] is None


def test_json_line_carries_the_traceback_of_a_logged_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record()
        record.exc_info = sys.exc_info()
        payload = _format(record)
    assert "ValueError: boom" in str(payload["exception"])


def test_console_format_produces_a_plain_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_FORMAT", "console")
    get_logging_config.cache_clear()
    handler = build_handler()
    record = _record()
    CorrelationIdFilter().filter(record)
    assert handler.formatter is not None
    assert "something happened" in handler.formatter.format(record)


def test_configure_logging_leaves_one_handler_and_the_configured_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")
    get_logging_config.cache_clear()
    configure_logging()
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1
    assert root_logger.level == logging.DEBUG


def test_configure_logging_makes_the_library_loggers_propagate() -> None:
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.propagate = False
    uvicorn_logger.addHandler(logging.NullHandler())
    configure_logging()
    assert uvicorn_logger.propagate
    assert uvicorn_logger.handlers == []
