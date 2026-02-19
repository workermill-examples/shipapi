"""Structured JSON access logging middleware for ShipAPI.

Emits one ``INFO``-level log record per request containing:

    ``method``, ``path``, ``status``, ``duration_ms``, ``request_id``

The ``request_id`` field is populated from :data:`~src.middleware.request_id.REQUEST_ID_CTX`
so it matches the ``X-Request-Id`` header when :class:`~src.middleware.request_id.RequestIdMiddleware`
is wired outermost.
"""

import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.middleware.request_id import REQUEST_ID_CTX

logger = logging.getLogger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Emit a structured JSON access-log record after every HTTP request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            json.dumps(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "request_id": REQUEST_ID_CTX.get(),
                }
            )
        )
        return response
