"""Tests for src/api/auth.py — register, login, refresh, and /me endpoints."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from src.api.auth import router as auth_router
from src.database import get_db
from src.models import User
from src.services.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    *,
    role: str = "user",
    is_active: bool = True,
    password: str = "secret123",
) -> MagicMock:
    """Return a MagicMock shaped like a User ORM instance."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "alice@example.com"
    user.name = "Alice"
    user.role = role
    user.password_hash = hash_password(password)
    user.is_active = is_active
    user.created_at = "2024-01-01T00:00:00Z"
    return user


def _make_app(db_mock: Any) -> FastAPI:
    """Build a minimal FastAPI app with the auth router and overridden DB."""
    app = FastAPI()
    app.include_router(auth_router)

    async def override_get_db() -> AsyncGenerator[Any]:
        yield db_mock

    app.dependency_overrides[get_db] = override_get_db
    return app


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success():
    """A new user can register and receives a one-time API key."""
    committed_users: list[Any] = []

    async def fake_commit() -> None:
        pass

    async def fake_refresh(obj: Any) -> None:
        # Simulate DB populating server-side defaults (id, role, timestamps)
        if not obj.id:
            obj.id = uuid.uuid4()
        obj.role = obj.role or "user"
        obj.is_active = True
        obj.created_at = "2024-01-01T00:00:00Z"

    db_mock = AsyncMock()
    db_mock.add = MagicMock(side_effect=lambda u: committed_users.append(u))
    db_mock.commit = AsyncMock(side_effect=fake_commit)
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)
    db_mock.rollback = AsyncMock()

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "password123", "name": "Alice"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["name"] == "Alice"
    assert "api_key" in data
    assert data["api_key"].startswith("sk_")
    assert len(data["api_key"]) == 67  # "sk_" + 64 hex chars
    # api_key must NOT be exposed in password_hash or other fields
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409():
    """Registering with an existing email returns 409 CONFLICT."""
    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock(side_effect=IntegrityError("dup", {}, Exception()))
    db_mock.rollback = AsyncMock()

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "password123", "name": "Alice"},
        )

    assert response.status_code == 409
    db_mock.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_short_password_returns_422():
    """Password shorter than 8 characters fails Pydantic validation."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "short", "name": "Alice"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_name_returns_422():
    """Whitespace-only name fails Pydantic validation."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={"email": "alice@example.com", "password": "password123", "name": "   "},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success():
    """Valid credentials return access and refresh tokens."""
    user = _make_user(password="password123")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 30 * 60  # default 30 minutes in seconds


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401():
    """Wrong password returns 401."""
    user = _make_user(password="correct_password")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": "wrong_password"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401():
    """Unknown email returns 401 (same as wrong password — no email enumeration)."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "unknown@example.com", "password": "password123"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401():
    """Inactive account returns 401."""
    user = _make_user(password="password123", is_active=False)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={"email": "alice@example.com", "password": "password123"},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success():
    """A valid refresh token returns a new token pair."""
    user = _make_user()
    refresh_token = create_refresh_token(str(user.id))

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401():
    """An access token must not be accepted on the refresh endpoint."""
    user = _make_user()
    access_token = create_access_token(str(user.id), user.email, user.role)

    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401():
    """A malformed refresh token returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": "not.a.valid.token"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_user_not_found_returns_401():
    """Valid refresh token but missing user row returns 401."""
    user_id = uuid.uuid4()
    refresh_token = create_refresh_token(str(user_id))

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=None)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_inactive_user_returns_401():
    """Valid refresh token but inactive user returns 401."""
    user = _make_user(is_active=False)
    refresh_token = create_refresh_token(str(user.id))

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_returns_current_user():
    """Authenticated user can retrieve their own profile."""
    user = _make_user()
    access_token = create_access_token(str(user.id), user.email, user.role)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    # Build app with both auth router (for /me) and dependency override
    app = FastAPI()
    app.include_router(auth_router)

    async def override_get_db() -> AsyncGenerator[Any]:
        yield db_mock

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
    assert data["name"] == user.name
    assert data["role"] == user.role
    assert "password_hash" not in data
    assert "api_key" not in data


@pytest.mark.asyncio
async def test_me_unauthenticated_returns_401():
    """Unauthenticated request to /me returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/auth/me")

    assert response.status_code == 401
