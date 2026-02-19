"""Request ID middleware for ShipAPI.

Assigns a UUID4 to every inbound request and exposes it via the ``X-Request-Id``
response header.  The ID is also stored in a ``ContextVar`` so other middleware
layers and application code can read it without touching the raw request object.

Ordering note
-------------
Add this middleware *last* via ``app.add_middleware`` so it is invoked *outermost*
(first-in, last-out) and covers all other layers.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Holds the request-scoped UUID for the duration of each request.
# Defaults to "" so consumers never receive ``None``.
REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a UUID4 ``X-Request-Id`` header to every HTTP response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        token = REQUEST_ID_CTX.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            REQUEST_ID_CTX.reset(token)
        response.headers["X-Request-Id"] = request_id
        return response
