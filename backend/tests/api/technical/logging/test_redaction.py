import logging

import pytest

from api.technical.logging.redaction import (
    REDACTED,
    AccessLogRedactionFilter,
    redact_path,
    redact_target,
)
from api.technical.logging.setup import configure_logging


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/public/articles/s3cr3t-token", f"/public/articles/{REDACTED}"),
        ("/inbound/newsletters/abc123", f"/inbound/newsletters/{REDACTED}"),
        ("/articles/42", "/articles/42"),
    ],
)
def test_a_token_carried_in_the_path_is_hidden(path: str, expected: str) -> None:
    assert redact_path(path) == expected


def test_secret_query_parameters_are_hidden_and_the_others_kept() -> None:
    target = "/fever/?api=&api_key=0123abcd&magic_token=zzz&page=2"

    redacted = redact_target(target)

    assert "0123abcd" not in redacted
    assert "zzz" not in redacted
    assert f"api_key={REDACTED}" in redacted
    assert "page=2" in redacted


def test_a_target_without_query_is_only_path_redacted() -> None:
    assert redact_target("/public/articles/tok") == f"/public/articles/{REDACTED}"


def test_the_access_log_filter_rewrites_the_request_line_of_a_uvicorn_record() -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1234", "GET", "/fever/?api_key=0123abcd", "1.1", 200),
        None,
    )

    assert AccessLogRedactionFilter().filter(record) is True

    assert "0123abcd" not in record.getMessage()
    assert REDACTED in record.getMessage()


def test_a_record_without_a_request_line_passes_untouched() -> None:
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, "plain", (), None)

    assert AccessLogRedactionFilter().filter(record) is True
    assert record.getMessage() == "plain"


def test_logging_setup_installs_the_filter_once() -> None:
    configure_logging()
    configure_logging()

    access_logger = logging.getLogger("uvicorn.access")
    installed = [
        item for item in access_logger.filters if isinstance(item, AccessLogRedactionFilter)
    ]
    assert len(installed) == 1
