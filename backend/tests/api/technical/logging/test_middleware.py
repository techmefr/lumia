import logging

import httpx
import pytest
from fastapi import FastAPI

from api.technical.logging.correlation import get_correlation_id
from api.technical.logging.middleware import REQUEST_ID_HEADER, CorrelationIdMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/echo-correlation-id")
    async def echo_correlation_id() -> dict[str, str | None]:
        return {"correlation_id": get_correlation_id()}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    return app


async def _get(path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers=headers)


async def test_answers_with_a_generated_request_id() -> None:
    response = await _get("/echo-correlation-id")
    assert response.headers[REQUEST_ID_HEADER]
    assert response.json()["correlation_id"] == response.headers[REQUEST_ID_HEADER]


async def test_reuses_the_request_id_the_caller_sent() -> None:
    response = await _get("/echo-correlation-id", headers={REQUEST_ID_HEADER: "trace-9"})
    assert response.headers[REQUEST_ID_HEADER] == "trace-9"
    assert response.json()["correlation_id"] == "trace-9"


async def test_replaces_a_forged_request_id() -> None:
    response = await _get("/echo-correlation-id", headers={REQUEST_ID_HEADER: "a b"})
    assert response.headers[REQUEST_ID_HEADER] != "a b"


async def test_logs_the_handled_request_with_its_correlation_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="lumia.request"):
        response = await _get("/echo-correlation-id", headers={REQUEST_ID_HEADER: "trace-1"})

    record = next(item for item in caplog.records if item.message == "request handled")
    assert record.method == "GET"  # type: ignore[attr-defined]
    assert record.path == "/echo-correlation-id"  # type: ignore[attr-defined]
    assert record.status_code == response.status_code  # type: ignore[attr-defined]
    assert record.correlation_id == "trace-1"  # type: ignore[attr-defined]


async def test_logs_a_failed_request_with_its_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="lumia.request"):
        await _get("/boom")

    record = next(item for item in caplog.records if item.message == "request failed")
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None


async def test_leaves_no_correlation_id_behind_after_the_response() -> None:
    await _get("/echo-correlation-id")
    assert get_correlation_id() is None
