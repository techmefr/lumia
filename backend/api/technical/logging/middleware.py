import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.technical.logging.correlation import (
    CORRELATION_ID_FIELD,
    reset_correlation_id,
    sanitize_correlation_id,
    set_correlation_id,
)

REQUEST_ID_HEADER = "X-Request-ID"
HTTP_REQUEST_EVENT = "http_request"

logger = logging.getLogger("lumia.request")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Gives every request an id, echoes it back and logs the request under it.

    Only the route path is logged, never the query string: a magic-link token travels there.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = sanitize_correlation_id(request.headers.get(REQUEST_ID_HEADER))
        token = set_correlation_id(correlation_id)
        started_at = time.perf_counter()
        request_fields = {
            "event": HTTP_REQUEST_EVENT,
            CORRELATION_ID_FIELD: correlation_id,
            "method": request.method,
            "path": request.url.path,
        }
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed",
                extra=request_fields | {"duration_ms": _elapsed_ms(started_at)},
            )
            raise
        else:
            response.headers[REQUEST_ID_HEADER] = correlation_id
            logger.info(
                "request handled",
                extra=request_fields
                | {"status_code": response.status_code, "duration_ms": _elapsed_ms(started_at)},
            )
            return response
        finally:
            reset_correlation_id(token)


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)
