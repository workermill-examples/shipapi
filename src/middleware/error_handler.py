"""Global exception handlers that return consistent JSON error envelopes.

Register these with the FastAPI application via ``app.add_exception_handler``.
All responses follow the ``ErrorResponse`` schema from ``src.schemas.common``.
"""

import logging
import traceback

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from src.schemas.common import ErrorCode, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

# Map HTTP status codes to stable error code strings used in the response envelope.
_STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _code_for_status(status_code: int) -> str:
    """Return the error code string for *status_code*, falling back to ``HTTP_{code}``."""
    return _STATUS_TO_CODE.get(status_code, f"HTTP_{status_code}")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert ``HTTPException`` to the standard error envelope.

    The ``exc.detail`` string becomes ``error.message``; the HTTP status code is
    translated to a stable ``error.code`` string (e.g. 404 → ``NOT_FOUND``).
    Any ``WWW-Authenticate`` or other response headers from the exception are
    forwarded to the client.
    """
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    body = ErrorResponse(
        error=ErrorCode(
            code=_code_for_status(exc.status_code),
            message=detail,
        )
    )
    headers = dict(exc.headers) if exc.headers else None
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
        headers=headers,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic / FastAPI ``RequestValidationError`` to the standard envelope.

    Each validation failure becomes an ``ErrorDetail`` with:
    - ``field``: dotted path (body-prefix stripped), e.g. ``"email"`` or ``"items.0.qty"``
    - ``message``: human-readable Pydantic message, e.g. ``"value is not a valid email address"``
    """
    details: list[ErrorDetail] = []
    for error in exc.errors():
        # ``loc`` is a tuple like ``("body", "email")`` or ``("query", "page")``.
        # Strip the leading "body" / "query" / "path" segment so callers see field names.
        loc = error["loc"]
        field_parts = [str(part) for part in loc if part not in ("body", "query", "path")]
        field = ".".join(field_parts) if field_parts else str(loc[-1]) if loc else "unknown"
        details.append(ErrorDetail(field=field, message=error["msg"]))

    body = ErrorResponse(
        error=ErrorCode(
            code="UNPROCESSABLE_ENTITY",
            message="Request validation failed",
            details=details,
        )
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=body.model_dump(),
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Convert SQLAlchemy ``IntegrityError`` to a 409 response.

    Unique-constraint violations (detected by inspecting the driver-level error
    string for the words ``"unique"`` or ``"duplicate"``) return code
    ``ALREADY_EXISTS``; all other integrity errors return ``CONFLICT``.
    """
    orig_str = str(exc.orig).lower() if exc.orig is not None else ""
    is_unique = "unique" in orig_str or "duplicate" in orig_str

    if is_unique:
        code = "ALREADY_EXISTS"
        message = "A resource with the given identifier already exists"
    else:
        code = "CONFLICT"
        message = "Database integrity constraint violation"

    body = ErrorResponse(error=ErrorCode(code=code, message=message))
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=body.model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for any exception not matched by a more specific handler.

    Logs the full traceback at ERROR level for server-side visibility, but
    returns only a generic ``INTERNAL_ERROR`` message to the client — no stack
    trace or internal details are ever exposed in the response body.
    """
    logger.error(
        "Unhandled %s on %s %s\n%s",
        type(exc).__name__,
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    body = ErrorResponse(
        error=ErrorCode(
            code="INTERNAL_ERROR",
            message="An internal server error occurred",
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=body.model_dump(),
    )
