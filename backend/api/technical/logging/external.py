import logging
from urllib.parse import urlsplit, urlunsplit

import httpx

EXTERNAL_CALL_FAILED_EVENT = "external_call_failed"
MAX_ERROR_LENGTH = 200


def redact_url(url: str) -> str:
    """Keeps only the stable part of a url: scheme, host, port and path.

    A query string or a userinfo part regularly carries an api key or a single-use token, and a log
    line outlives the call it describes.
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    netloc = f"{host}:{parts.port}" if parts.port is not None else host
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def describe_error(error: BaseException) -> str:
    """The error type plus a truncated message: a provider's error body can be arbitrarily long.

    An httpx status error spells the whole request url out in its message, query string included,
    so only its type is kept: the url travels next to it, redacted, and so does the status.
    """
    if isinstance(error, httpx.HTTPStatusError):
        return type(error).__name__
    message = str(error)[:MAX_ERROR_LENGTH]
    return f"{type(error).__name__}: {message}" if message else type(error).__name__


def log_external_failure(
    logger: logging.Logger,
    *,
    service: str,
    operation: str,
    url: str | None = None,
    status_code: int | None = None,
    error: str | None = None,
) -> None:
    logger.warning(
        "external call failed",
        extra={
            "event": EXTERNAL_CALL_FAILED_EVENT,
            "service": service,
            "operation": operation,
            "url": redact_url(url) if url is not None else None,
            "status_code": status_code,
            "error": error,
        },
    )
