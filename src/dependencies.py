"""FastAPI dependencies: DB session, current-user extraction, and role guards."""

import uuid

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import User
from src.services.auth import decode_token, verify_api_key

__all__ = ["get_db", "get_current_user", "require_admin"]

# Security scheme extractors registered in the OpenAPI spec so Swagger UI shows
# the "Authorize" button with both Bearer-token and API-key options.
_bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    description="JWT access token. Obtain one via **POST /api/v1/auth/login**, then paste the `access_token` value here.",
    auto_error=False,
)
_api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    description="API key issued at registration (returned once in the `api_key` field). Demo key: `sk_demo_shipapi_2026_showcase_key`.",
    auto_error=False,
)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),  # noqa: B008
    api_key: str | None = Security(_api_key_header),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> User:
    """Return the authenticated ``User`` from Bearer JWT or ``X-API-Key`` header.

    The Authorization header (Bearer JWT) is checked first; ``X-API-Key`` is the
    fallback.  Raises ``HTTP 401`` if neither credential is present or valid.
    """
    if bearer is not None:
        return await _user_from_token(bearer.credentials, db)

    if api_key is not None:
        return await _user_from_api_key(api_key, db)

    raise _CREDENTIALS_EXCEPTION


async def require_admin(current_user: User = Depends(get_current_user)) -> User:  # noqa: B008
    """Require the ``admin`` role.  Raises ``HTTP 403`` for non-admin users."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _user_from_token(token: str, db: AsyncSession) -> User:
    """Resolve a Bearer JWT to a live, active ``User`` row."""
    try:
        payload = decode_token(token)
    except JWTError:
        raise _CREDENTIALS_EXCEPTION from None

    if payload.get("type") != "access":
        raise _CREDENTIALS_EXCEPTION

    raw_id: str | None = payload.get("sub")
    if not raw_id:
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(raw_id)
    except ValueError:
        raise _CREDENTIALS_EXCEPTION from None

    user: User | None = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


async def _user_from_api_key(api_key: str, db: AsyncSession) -> User:
    """Resolve an ``X-API-Key`` value to a live, active ``User`` row."""
    prefix = api_key[:8]
    result = await db.execute(select(User).where(User.api_key_prefix == prefix))
    user: User | None = result.scalar_one_or_none()

    if user is None or user.api_key_hash is None:
        raise _CREDENTIALS_EXCEPTION

    if not verify_api_key(api_key, user.api_key_hash):
        raise _CREDENTIALS_EXCEPTION

    if not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user
