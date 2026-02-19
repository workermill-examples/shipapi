"""Integration tests verifying the standard error envelope across all error codes.

All error responses from the ShipAPI must conform to:

    {"error": {"code": "...", "message": "...", "details": [...]}}

Where ``details`` is a list present only for 422 validation errors.

Covers:
- HTTP 404 (NOT_FOUND) — non-existent resource (category by fake UUID)
- HTTP 422 (UNPROCESSABLE_ENTITY) — invalid request body, with field-level details
- HTTP 409 (CONFLICT) — duplicate email registration
- HTTP 401 (UNAUTHORIZED) — unauthenticated request to a protected endpoint
- HTTP 403 (FORBIDDEN) — authenticated non-admin user on admin-only endpoint

All tests run against the real test PostgreSQL database via the ``async_client``
fixture.  Error assertions use ``response.json()["error"]["..."]`` because the
global ``http_exception_handler`` wraps all ``HTTPException`` responses in the
project's ``ErrorResponse`` envelope (not FastAPI's default ``detail`` format).
"""

import uuid

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# 404 — NOT_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_404_returns_standard_error_format(async_client: AsyncClient) -> None:
    """A request for a non-existent category returns HTTP 404 with the error envelope."""
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/categories/{fake_id}")
    assert resp.status_code == 404

    body = resp.json()
    assert "error" in body, f"Missing 'error' key in response: {body}"
    assert body["error"]["code"] == "NOT_FOUND"
    assert isinstance(body["error"]["message"], str)
    assert len(body["error"]["message"]) > 0


@pytest.mark.asyncio
async def test_404_details_field_is_null(async_client: AsyncClient) -> None:
    """A 404 error response has ``details`` set to null (not populated for HTTP errors)."""
    fake_id = str(uuid.uuid4())
    resp = await async_client.get(f"/api/v1/categories/{fake_id}")
    assert resp.status_code == 404
    assert resp.json()["error"]["details"] is None


# ---------------------------------------------------------------------------
# 422 — UNPROCESSABLE_ENTITY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_422_returns_standard_error_format(async_client: AsyncClient) -> None:
    """An invalid request body returns HTTP 422 with the standard error envelope."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "name": "Test", "password": "TestPassword123!"},
    )
    assert resp.status_code == 422

    body = resp.json()
    assert "error" in body, f"Missing 'error' key in response: {body}"
    assert body["error"]["code"] == "UNPROCESSABLE_ENTITY"
    assert body["error"]["message"] == "Request validation failed"


@pytest.mark.asyncio
async def test_422_includes_field_level_details(async_client: AsyncClient) -> None:
    """A 422 response includes a non-empty ``details`` list with field-level errors."""
    resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "name": "Test", "password": "TestPassword123!"},
    )
    assert resp.status_code == 422

    details = resp.json()["error"]["details"]
    assert isinstance(details, list), f"Expected list, got: {type(details)}"
    assert len(details) > 0, "details list must not be empty for 422 responses"

    entry = details[0]
    assert "field" in entry, f"Each detail must have a 'field' key, got: {entry}"
    assert "message" in entry, f"Each detail must have a 'message' key, got: {entry}"


# ---------------------------------------------------------------------------
# 409 — CONFLICT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_409_returns_standard_error_format(async_client: AsyncClient) -> None:
    """A duplicate-resource request returns HTTP 409 with the standard error envelope."""
    email = f"dup_{uuid.uuid4().hex[:8]}@test.com"
    payload = {"email": email, "name": "Test User", "password": "TestPassword123!"}

    first = await async_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await async_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409

    body = second.json()
    assert "error" in body, f"Missing 'error' key in response: {body}"
    assert body["error"]["code"] == "CONFLICT"
    assert isinstance(body["error"]["message"], str)
    assert len(body["error"]["message"]) > 0


@pytest.mark.asyncio
async def test_409_details_field_is_null(async_client: AsyncClient) -> None:
    """A 409 error response has ``details`` set to null."""
    email = f"dup2_{uuid.uuid4().hex[:8]}@test.com"
    payload = {"email": email, "name": "Test User", "password": "TestPassword123!"}

    await async_client.post("/api/v1/auth/register", json=payload)
    second = await async_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["details"] is None


# ---------------------------------------------------------------------------
# 401 — UNAUTHORIZED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_401_returns_standard_error_format(async_client: AsyncClient) -> None:
    """An unauthenticated request to a protected endpoint returns HTTP 401."""
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    body = resp.json()
    assert "error" in body, f"Missing 'error' key in response: {body}"
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert isinstance(body["error"]["message"], str)
    assert len(body["error"]["message"]) > 0


@pytest.mark.asyncio
async def test_401_details_field_is_null(async_client: AsyncClient) -> None:
    """A 401 error response has ``details`` set to null."""
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["details"] is None


# ---------------------------------------------------------------------------
# 403 — FORBIDDEN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_403_returns_standard_error_format(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """A non-admin request to an admin-only endpoint returns HTTP 403."""
    resp = await async_client.post(
        "/api/v1/categories",
        json={"name": "Test Category"},
        headers=auth_headers,
    )
    assert resp.status_code == 403

    body = resp.json()
    assert "error" in body, f"Missing 'error' key in response: {body}"
    assert body["error"]["code"] == "FORBIDDEN"
    assert isinstance(body["error"]["message"], str)
    assert len(body["error"]["message"]) > 0


@pytest.mark.asyncio
async def test_403_details_field_is_null(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """A 403 error response has ``details`` set to null."""
    resp = await async_client.post(
        "/api/v1/categories",
        json={"name": "Test Category"},
        headers=auth_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["details"] is None
