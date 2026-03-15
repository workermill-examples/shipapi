"""ASGI middleware for ShipAPI.

Pure ASGI middleware implementation (NOT BaseHTTPMiddleware):
- RequestIdMiddleware: Adds X-Request-Id header to every response
- AccessLogMiddleware: Logs all requests with structured format

Both middleware are optimized for performance and follow ASGI 3.0 spec.
"""

import json
import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    """Add X-Request-Id header to every response for request tracing."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate or extract request ID
        request_id = str(uuid.uuid4())

        # Add request ID to scope for potential use by other middleware/handlers
        scope["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)


class AccessLogMiddleware:
    """Log all HTTP requests with structured format."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        status_code = 500
        response_size = 0

        async def send_with_logging(message: Message) -> None:
            nonlocal status_code, response_size

            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_size += len(body)

            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        finally:
            # Log the request
            duration_ms = (time.time() - start_time) * 1000

            # Extract request details from scope
            method = scope["method"]
            path = scope["path"]
            query_string = scope.get("query_string", b"").decode("latin1")
            if query_string:
                path = f"{path}?{query_string}"

            # Extract client IP
            client = scope.get("client", ("unknown", 0))
            client_ip = client[0] if client else "unknown"

            # Extract User-Agent
            user_agent = "unknown"
            for name, value in scope.get("headers", []):
                if name == b"user-agent":
                    user_agent = value.decode("latin1")
                    break

            # Extract request ID from scope
            request_id = scope.get("request_id", "unknown")

            # Structured log entry
            log_data = {
                "timestamp": time.time(),
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "response_size": response_size,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }

            # Log as structured JSON
            logger.info("HTTP request completed", extra={"log_data": json.dumps(log_data)})


# Convenience function to add middleware to FastAPI app
def add_middleware(app: ASGIApp) -> ASGIApp:
    """
    Add all middleware to the FastAPI application.

    Order matters: RequestIdMiddleware should be outermost so X-Request-Id
    is available to AccessLogMiddleware.
    """
    # Apply middleware in reverse order (outermost first)
    app = AccessLogMiddleware(app)
    app = RequestIdMiddleware(app)
    return app
