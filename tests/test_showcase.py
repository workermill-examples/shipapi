"""Tests for GET / (landing page) and GET /api/v1/showcase/stats (public stats)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_landing_page_returns_200(async_client: AsyncClient) -> None:
    """Root URL returns HTTP 200."""
    response = await async_client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_landing_page_content_type_html(async_client: AsyncClient) -> None:
    """Root URL returns HTML content type."""
    response = await async_client.get("/")
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_landing_page_contains_shipapi(async_client: AsyncClient) -> None:
    """Landing page HTML mentions ShipAPI."""
    response = await async_client.get("/")
    assert "ShipAPI" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_workermill(async_client: AsyncClient) -> None:
    """Landing page HTML includes WorkerMill branding."""
    response = await async_client.get("/")
    assert "WorkerMill" in response.text or "workermill" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_demo_credentials(async_client: AsyncClient) -> None:
    """Landing page includes demo email and API key."""
    response = await async_client.get("/")
    assert "demo@workermill.com" in response.text
    assert "sk_demo_shipapi_2026_showcase_key" in response.text


@pytest.mark.asyncio
async def test_stats_returns_200(async_client: AsyncClient) -> None:
    """Showcase stats endpoint returns HTTP 200."""
    response = await async_client.get("/api/v1/showcase/stats")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stats_no_auth_required(async_client: AsyncClient) -> None:
    """Showcase stats endpoint is public — no auth header needed."""
    response = await async_client.get("/api/v1/showcase/stats")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stats_response_schema(async_client: AsyncClient) -> None:
    """Stats response contains exactly the expected integer fields."""
    response = await async_client.get("/api/v1/showcase/stats")
    body = response.json()

    required_keys = {
        "products",
        "categories",
        "warehouses",
        "stock_alerts",
        "stock_transfers",
        "audit_log_entries",
    }
    assert set(body.keys()) == required_keys
    for key in required_keys:
        assert isinstance(body[key], int), f"{key} should be int, got {type(body[key])}"


@pytest.mark.asyncio
async def test_stats_non_negative(async_client: AsyncClient) -> None:
    """All stats values are non-negative integers."""
    response = await async_client.get("/api/v1/showcase/stats")
    body = response.json()
    for key, value in body.items():
        assert value >= 0, f"{key} should be >= 0, got {value}"


@pytest.mark.asyncio
async def test_stats_content_type_json(async_client: AsyncClient) -> None:
    """Stats endpoint returns JSON content type."""
    response = await async_client.get("/api/v1/showcase/stats")
    assert "application/json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_stats_reflects_seeded_data(
    async_client: AsyncClient, seeded_db: dict
) -> None:  # noqa: ARG001
    """Stats counts match seeded data: 3 products, 2 categories, 2 warehouses."""
    response = await async_client.get("/api/v1/showcase/stats")
    body = response.json()

    # seeded_db creates 3 active products, 2 categories, 2 warehouses
    assert body["products"] == 3
    assert body["categories"] == 2
    assert body["warehouses"] == 2
    # product2 has quantity=5 < min_threshold=20 → 1 alert
    assert body["stock_alerts"] == 1
