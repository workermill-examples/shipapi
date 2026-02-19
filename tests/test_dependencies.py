"""Tests for src/dependencies.py — get_current_user and require_admin."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from src.database import get_db
from src.dependencies import get_current_user, require_admin
from src.models import User
from src.services.auth import (
    create_access_token,
    create_refresh_token,
    generate_api_key,
    hash_api_key,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    *,
    role: str = "user",
    is_active: bool = True,
    api_key: str | None = None,
) -> MagicMock:
    """Return a MagicMock shaped like a User ORM instance."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "alice@example.com"
    user.name = "Alice"
    user.role = role
    user.password_hash = "hashed"
    user.is_active = is_active
    user.api_key_prefix = api_key[:8] if api_key else None
    user.api_key_hash = hash_api_key(api_key) if api_key else None
    return user


@asynccontextmanager
async def _make_client(db_mock: Any) -> AsyncGenerator[AsyncClient]:
    """Build an AsyncClient with a minimal test app and get_db overridden."""
    mini_app = FastAPI()

    @mini_app.get("/protected")
    async def protected(current_user: User = Depends(get_current_user)):  # noqa: B008
        return {
            "id": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role,
        }

    @mini_app.get("/admin")
    async def admin_only(current_user: User = Depends(require_admin)):  # noqa: B008
        return {"id": str(current_user.id), "role": current_user.role}

    async def override_get_db() -> AsyncGenerator[Any]:
        yield db_mock

    mini_app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=mini_app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Bearer JWT — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bearer_valid_token_returns_user():
    """A valid access-token JWT resolves to the matching user."""
    user = _make_user()
    token = create_access_token(str(user.id), user.email, user.role)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    async with _make_client(db_mock) as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
    assert data["role"] == user.role


# ---------------------------------------------------------------------------
# Bearer JWT — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bearer_invalid_token_returns_401():
    """A malformed JWT raises 401."""
    db_mock = AsyncMock()

    async with _make_client(db_mock) as client:
        response = await client.get(
            "/protected", headers={"Authorization": "Bearer not.a.valid.token"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bearer_refresh_token_returns_401():
    """A refresh token must NOT be accepted on protected routes."""
    user = _make_user()
    refresh = create_refresh_token(str(user.id))

    db_mock = AsyncMock()

    async with _make_client(db_mock) as client:
        response = await client.get(
            "/protected", headers={"Authorization": f"Bearer {refresh}"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bearer_user_not_found_returns_401():
    """Valid JWT but user row missing from DB raises 401."""
    user = _make_user()
    token = create_access_token(str(user.id), user.email, user.role)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=None)

    async with _make_client(db_mock) as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bearer_inactive_user_returns_401():
    """Valid JWT but inactive user raises 401."""
    user = _make_user(is_active=False)
    token = create_access_token(str(user.id), user.email, user.role)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    async with _make_client(db_mock) as client:
        response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# API key — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_valid_returns_user():
    """A valid X-API-Key resolves to the matching user."""
    raw_key = generate_api_key()
    user = _make_user(api_key=raw_key)

    db_mock = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db_mock.execute = AsyncMock(return_value=mock_result)

    async with _make_client(db_mock) as client:
        response = await client.get("/protected", headers={"X-API-Key": raw_key})

    assert response.status_code == 200
    assert response.json()["email"] == user.email


# ---------------------------------------------------------------------------
# API key — error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_key_wrong_secret_returns_401():
    """Correct prefix but wrong secret part raises 401."""
    raw_key = generate_api_key()
    user = _make_user(api_key=raw_key)

    # Tamper: same prefix, different secret
    tampered_key = raw_key[:8] + "x" * (len(raw_key) - 8)

    db_mock = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db_mock.execute = AsyncMock(return_value=mock_result)

    async with _make_client(db_mock) as client:
        response = await client.get("/protected", headers={"X-API-Key": tampered_key})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_key_prefix_not_found_returns_401():
    """API key with unknown prefix raises 401."""
    raw_key = generate_api_key()

    db_mock = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_mock.execute = AsyncMock(return_value=mock_result)

    async with _make_client(db_mock) as client:
        response = await client.get("/protected", headers={"X-API-Key": raw_key})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_key_inactive_user_returns_401():
    """Valid API key but inactive user raises 401."""
    raw_key = generate_api_key()
    user = _make_user(api_key=raw_key, is_active=False)

    db_mock = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db_mock.execute = AsyncMock(return_value=mock_result)

    async with _make_client(db_mock) as client:
        response = await client.get("/protected", headers={"X-API-Key": raw_key})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# No credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_credentials_returns_401():
    """Missing Authorization and X-API-Key headers raise 401."""
    db_mock = AsyncMock()

    async with _make_client(db_mock) as client:
        response = await client.get("/protected")

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Bearer takes priority over API key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bearer_takes_priority_over_api_key():
    """When both Bearer and X-API-Key are present, Bearer wins."""
    user = _make_user()
    token = create_access_token(str(user.id), user.email, user.role)
    raw_key = generate_api_key()

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    async with _make_client(db_mock) as client:
        response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}", "X-API-Key": raw_key},
        )

    assert response.status_code == 200
    # db.get was called (JWT path), not db.execute (API key path)
    db_mock.get.assert_awaited_once()
    db_mock.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# require_admin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_admin_passes_for_admin():
    """Admin user passes the require_admin guard."""
    user = _make_user(role="admin")
    token = create_access_token(str(user.id), user.email, user.role)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    async with _make_client(db_mock) as client:
        response = await client.get("/admin", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_require_admin_rejects_non_admin():
    """Non-admin user is rejected with 403."""
    user = _make_user(role="user")
    token = create_access_token(str(user.id), user.email, user.role)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    async with _make_client(db_mock) as client:
        response = await client.get("/admin", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
