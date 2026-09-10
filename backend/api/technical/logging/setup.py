import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from api.technical.logging.correlation import CORRELATION_ID_FIELD, get_correlation_id
from config.logging import LogFormat, get_logging_config

CONSOLE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s [%(correlation_id)s] %(message)s"

# Attributes every LogRecord carries. Anything else on the record came from an `extra=` mapping
# and is a field the caller wants in the log line.
_RECORD_OWN_ATTRIBUTES = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "stacklevel",
        "taskName",
        "thread",
        "threadName",
    }
)


class CorrelationIdFilter(logging.Filter):
    """Puts the current correlation id on every record, including the ones libraries emit."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, CORRELATION_ID_FIELD):
            setattr(record, CORRELATION_ID_FIELD, get_correlation_id())
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RECORD_OWN_ATTRIBUTES and not key.startswith("_"):
                payload[key] = value
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if get_logging_config().log_format is LogFormat.JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    handler.addFilter(CorrelationIdFilter())
    return handler


def configure_logging() -> None:
    """Routes every logger of the process through one handler.

    uvicorn and arq install handlers of their own on import, which is why theirs are dropped and
    made to propagate: one process has to produce one log shape, or a log aggregator sees two.
    """
    config = get_logging_config()
    root_logger = logging.getLogger()
    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)
    root_logger.addHandler(build_handler())
    root_logger.setLevel(config.log_level.upper())
    for library_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "arq", "arq.worker"):
        library_logger = logging.getLogger(library_logger_name)
        library_logger.handlers.clear()
        library_logger.propagate = True
