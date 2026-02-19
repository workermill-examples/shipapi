"""Rate limiting infrastructure using slowapi.

Provides a configured :class:`~slowapi.Limiter` instance together with key-function
variants and the request/response components needed to enforce per-endpoint limits
and inject standard rate-limit response headers.

Key functions
-------------
``get_remote_address`` (re-exported from slowapi)
    IP-based key, suitable for unauthenticated endpoints (register, login, refresh).

``get_user_key``
    Extracts a stable per-user key from the inbound request:

    1. **Bearer JWT** — decodes the ``sub`` claim (user UUID) as ``"user:<uuid>"``.
       Token expiry is intentionally skipped; authentication dependencies handle
       expiry enforcement separately.
    2. **X-API-Key header** — SHA-256 hashes the raw key and uses the first 16 hex
       characters as ``"apikey:<prefix>"``.
    3. **IP address** — fallback via :func:`~slowapi.util.get_remote_address`.

Per-endpoint rate limits (auth router)
---------------------------------------

+---------------------+---------------+---------------------+
| Endpoint            | Limit         | Key function        |
+=====================+===============+=====================+
| POST /auth/register | 5/minute      | IP (remote address) |
+---------------------+---------------+---------------------+
| POST /auth/login    | 10/minute     | IP (remote address) |
+---------------------+---------------+---------------------+
| POST /auth/refresh  | 30/minute     | IP (remote address) |
+---------------------+---------------+---------------------+
| GET  /auth/me       | 100/minute    | user/API-key based  |
+---------------------+---------------+---------------------+

Wiring in ``main.py``
---------------------
::

    from slowapi.errors import RateLimitExceeded
    from src.middleware.rate_limit import limiter, rate_limit_exceeded_handler

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

Applying decorators on endpoints
---------------------------------
Each rate-limited endpoint must accept ``request: Request`` and
``response: Response`` parameters so slowapi can inject the rate-limit
response headers::

    from fastapi import Request, Response
    from src.middleware.rate_limit import limiter, get_user_key

    @router.get("/me")
    @limiter.limit("100/minute", key_func=get_user_key)
    async def me(request: Request, response: Response, ...) -> UserResponse:
        ...
"""

import hashlib
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError
from jose import jwt as _jose_jwt
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import Response

from src.config import settings
from src.schemas.common import ErrorCode, ErrorResponse

__all__ = [
    "limiter",
    "get_remote_address",
    "get_user_key",
    "rate_limit_exceeded_handler",
]


def get_user_key(request: Request) -> str:
    """Extract a stable per-user rate-limit key from the request.

    Precedence:
    1. Bearer JWT ``sub`` claim → ``"user:<uuid>"``
    2. ``X-API-Key`` SHA-256 prefix → ``"apikey:<16-hex-chars>"``
    3. Client IP address (fallback via :func:`~slowapi.util.get_remote_address`)
    """
    # 1. Try Bearer JWT (skip expiry check — auth deps enforce that separately)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload: dict[str, Any] = _jose_jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            user_id = payload.get("sub")
            if isinstance(user_id, str) and user_id:
                return f"user:{user_id}"
        except JWTError:
            pass

    # 2. Try X-API-Key header
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"apikey:{key_hash}"

    # 3. Fall back to remote IP address
    return get_remote_address(request)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """Return 429 with the standard error envelope when a rate limit is exceeded.

    ``X-RateLimit-*`` and ``Retry-After`` headers are injected by calling
    :meth:`~slowapi.Limiter._inject_headers` on the app's limiter instance,
    which reads ``request.state.view_rate_limit`` set by slowapi before raising
    the exception.
    """
    body = ErrorResponse(
        error=ErrorCode(
            code="RATE_LIMITED",
            message="Rate limit exceeded. Please try again later.",
        )
    )
    resp: Response = JSONResponse(
        status_code=429,
        content=body.model_dump(),
    )
    view_rate_limit = getattr(request.state, "view_rate_limit", None)
    if view_rate_limit is not None:
        try:
            app_limiter: Limiter | None = getattr(request.app.state, "limiter", None)
            if app_limiter is not None:
                resp = app_limiter._inject_headers(resp, view_rate_limit)
        except Exception:  # noqa: BLE001
            pass
    return resp


# ---------------------------------------------------------------------------
# Limiter singleton
# ---------------------------------------------------------------------------

#: Shared rate-limiter instance.  Uses in-memory storage (resets on container
#: restart — acceptable for a single-instance showcase deployment).
#:
#: ``headers_enabled=True`` enables ``X-RateLimit-*`` header injection by the
#: ``@limiter.limit()`` decorator when the decorated endpoint declares a
#: ``response: Response`` parameter.
limiter: Limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
