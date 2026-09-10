import logging

import httpx
import pytest

from api.technical.logging.external import (
    MAX_ERROR_LENGTH,
    describe_error,
    log_external_failure,
    redact_url,
)


def test_redact_url_drops_the_query_string() -> None:
    assert redact_url("https://provider.test/v1/x?key=secret") == "https://provider.test/v1/x"


def test_redact_url_drops_the_userinfo() -> None:
    assert redact_url("https://admin:pass@provider.test/v1/feeds") == (
        "https://provider.test/v1/feeds"
    )


def test_redact_url_keeps_a_non_default_port() -> None:
    assert redact_url("http://miniflux.test:8080/v1/feeds") == "http://miniflux.test:8080/v1/feeds"


def test_describe_error_names_the_type_and_truncates_the_message() -> None:
    described = describe_error(httpx.ConnectError("x" * (MAX_ERROR_LENGTH + 50)))
    assert described.startswith("ConnectError: ")
    assert len(described) == len("ConnectError: ") + MAX_ERROR_LENGTH


def test_log_external_failure_records_the_service_the_url_and_the_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = logging.getLogger("lumia.test.external")
    with caplog.at_level(logging.WARNING, logger="lumia.test.external"):
        log_external_failure(
            logger,
            service="deepl",
            operation="translate",
            url="https://api.test/v2/translate?auth_key=secret",
            status_code=456,
        )

    record = caplog.records[-1]
    assert record.service == "deepl"  # type: ignore[attr-defined]
    assert record.operation == "translate"  # type: ignore[attr-defined]
    assert record.status_code == 456  # type: ignore[attr-defined]
    assert record.url == "https://api.test/v2/translate"  # type: ignore[attr-defined]


def test_describe_error_keeps_the_url_out_of_a_status_error_message() -> None:
    request = httpx.Request("GET", "https://provider.test/v1/x?key=secret")
    error = httpx.HTTPStatusError(
        "Client error for url https://provider.test/v1/x?key=secret",
        request=request,
        response=httpx.Response(401, request=request),
    )
    assert describe_error(error) == "HTTPStatusError"
