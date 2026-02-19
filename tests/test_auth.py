"""Tests for the Auth endpoints: register, login, refresh, and /me.

Covers:
- POST /api/v1/auth/register — happy path (201 + api_key), duplicate email (409),
  invalid payload (422)
- POST /api/v1/auth/login — valid credentials (200 + tokens), invalid credentials (401)
- POST /api/v1/auth/refresh — valid refresh token (new access token), access token
  reused as refresh (401), invalid token format (401)
- GET /api/v1/auth/me — with JWT (200), with X-API-Key (200), no auth (401),
  expired/invalid token (401)

All tests run against the real test PostgreSQL database via the async_client fixture.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from src.config import settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unique_email(prefix: str = "user") -> str:
    """Return an email address guaranteed not to collide with other test calls."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"


def _register_payload(
    email: str | None = None,
    password: str = "ValidPass123!",
    name: str = "Test User",
) -> dict[str, str]:
    return {
        "email": email or _unique_email(),
        "password": password,
        "name": name,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_returns_201(async_client: AsyncClient) -> None:
    """Successful registration returns HTTP 201."""
    response = await async_client.post("/api/v1/auth/register", json=_register_payload())
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_returns_api_key(async_client: AsyncClient) -> None:
    """Registration response includes a one-time api_key."""
    response = await async_client.post("/api/v1/auth/register", json=_register_payload())
    body = response.json()
    assert "api_key" in body
    assert isinstance(body["api_key"], str)
    assert body["api_key"].startswith("sk_")


@pytest.mark.asyncio
async def test_register_response_schema(async_client: AsyncClient) -> None:
    """Registration response contains id, email, name, role, created_at, and api_key."""
    payload = _register_payload()
    response = await async_client.post("/api/v1/auth/register", json=payload)
    body = response.json()

    assert "id" in body
    assert body["email"] == payload["email"]
    assert body["name"] == payload["name"]
    assert body["role"] == "user"
    assert "created_at" in body
    assert "api_key" in body


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(async_client: AsyncClient) -> None:
    """Registering with an already-registered email returns HTTP 409."""
    payload = _register_payload()
    first = await async_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await async_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert "already registered" in second.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_short_password_returns_422(async_client: AsyncClient) -> None:
    """Registering with a password shorter than 8 characters returns HTTP 422."""
    payload = _register_payload(password="short")
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_name_returns_422(async_client: AsyncClient) -> None:
    """Registering with an empty (whitespace-only) name returns HTTP 422."""
    payload = _register_payload(name="   ")
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(async_client: AsyncClient) -> None:
    """Registering with a malformed email address returns HTTP 422."""
    payload = _register_payload(email="not-an-email")
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_200_with_tokens(async_client: AsyncClient) -> None:
    """Logging in with valid credentials returns HTTP 200 with access and refresh tokens."""
    payload = _register_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert isinstance(body["expires_in"], int)


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(async_client: AsyncClient) -> None:
    """Logging in with the wrong password returns HTTP 401."""
    payload = _register_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "WrongPassword!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401(async_client: AsyncClient) -> None:
    """Logging in for an email that was never registered returns HTTP 401."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": _unique_email("ghost"), "password": "SomePassword123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_access_token_is_valid_jwt(async_client: AsyncClient) -> None:
    """The access token returned by login decodes as a valid JWT with expected claims."""
    payload = _register_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    token = login_resp.json()["access_token"]
    decoded = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

    assert decoded["type"] == "access"
    assert decoded["email"] == payload["email"]
    assert "sub" in decoded


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(async_client: AsyncClient) -> None:
    """Exchanging a valid refresh token yields a new access token."""
    payload = _register_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    body = refresh_resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401(async_client: AsyncClient) -> None:
    """Using an access token as a refresh token returns HTTP 401 (wrong token type)."""
    payload = _register_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    access_token = login_resp.json()["access_token"]

    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(async_client: AsyncClient) -> None:
    """Sending a garbage string as a refresh token returns HTTP 401."""
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not.a.valid.jwt"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_expired_token_returns_401(async_client: AsyncClient) -> None:
    """An expired refresh token returns HTTP 401."""
    payload = _register_payload()
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    user_id = reg_resp.json()["id"]

    expired_token = jwt.encode(
        {
            "sub": user_id,
            "type": "refresh",
            "exp": datetime.now(UTC) - timedelta(days=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_token},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_with_jwt_returns_user_profile(async_client: AsyncClient) -> None:
    """GET /me with a valid JWT Bearer token returns the authenticated user's profile."""
    payload = _register_payload()
    await async_client.post("/api/v1/auth/register", json=payload)

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    access_token = login_resp.json()["access_token"]

    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    me_body = me_resp.json()
    assert me_body["email"] == payload["email"]
    assert me_body["name"] == payload["name"]
    assert "id" in me_body
    assert "role" in me_body
    assert "created_at" in me_body
    # api_key must NOT be exposed on the /me endpoint (security)
    assert "api_key" not in me_body


@pytest.mark.asyncio
async def test_me_with_api_key_returns_user_profile(async_client: AsyncClient) -> None:
    """GET /me with a valid X-API-Key header returns the authenticated user's profile."""
    payload = _register_payload()
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    api_key = reg_resp.json()["api_key"]

    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": api_key},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == payload["email"]


@pytest.mark.asyncio
async def test_me_without_auth_returns_401(async_client: AsyncClient) -> None:
    """GET /me without any credentials returns HTTP 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(async_client: AsyncClient) -> None:
    """GET /me with a malformed Bearer token returns HTTP 401."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer totally-not-a-jwt"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_expired_token_returns_401(async_client: AsyncClient) -> None:
    """GET /me with an expired JWT returns HTTP 401."""
    payload = _register_payload()
    reg_resp = await async_client.post("/api/v1/auth/register", json=payload)
    user_id = reg_resp.json()["id"]

    expired_token = jwt.encode(
        {
            "sub": user_id,
            "email": payload["email"],
            "role": "user",
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_api_key_returns_401(async_client: AsyncClient) -> None:
    """GET /me with a syntactically valid but unrecognized API key returns HTTP 401."""
    fake_key = "sk_" + "a" * 64
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": fake_key},
    )
    assert response.status_code == 401
