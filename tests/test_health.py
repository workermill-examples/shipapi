"""Tests for GET /api/v1/health — liveness probe endpoint.

All tests in this module use the real test database via the ``async_client``
fixture.  The health endpoint always returns HTTP 200 (Railway liveness
probe requirement); database reachability is communicated in the JSON body.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(async_client: AsyncClient) -> None:
    """Health endpoint always returns HTTP 200."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_status_ok(async_client: AsyncClient) -> None:
    """Health endpoint reports status 'ok' when the database is reachable."""
    response = await async_client.get("/api/v1/health")
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_database_connected(async_client: AsyncClient) -> None:
    """Health endpoint reports database 'connected' against the test DB."""
    response = await async_client.get("/api/v1/health")
    assert response.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_health_version(async_client: AsyncClient) -> None:
    """Health endpoint includes the application version string."""
    response = await async_client.get("/api/v1/health")
    assert response.json()["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health_built_by(async_client: AsyncClient) -> None:
    """Health endpoint includes the built_by field matching the app name."""
    response = await async_client.get("/api/v1/health")
    assert response.json()["built_by"] == "ShipAPI"


@pytest.mark.asyncio
async def test_health_response_schema(async_client: AsyncClient) -> None:
    """Health response contains exactly the expected fields with correct types."""
    response = await async_client.get("/api/v1/health")
    body = response.json()

    assert isinstance(body["status"], str)
    assert isinstance(body["database"], str)
    assert isinstance(body["version"], str)
    assert isinstance(body["built_by"], str)
    # Verify no unexpected extra keys beyond the four documented fields.
    assert set(body.keys()) == {"status", "database", "version", "built_by"}


@pytest.mark.asyncio
async def test_health_content_type_json(async_client: AsyncClient) -> None:
    """Health endpoint returns a JSON content-type header."""
    response = await async_client.get("/api/v1/health")
    assert "application/json" in response.headers["content-type"]
