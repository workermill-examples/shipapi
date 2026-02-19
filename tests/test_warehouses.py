"""Integration tests for the Warehouse CRUD endpoints.

Covers:
- POST /api/v1/warehouses (admin) — create warehouse, response schema
- GET  /api/v1/warehouses      — list with pagination envelope
- GET  /api/v1/warehouses/{id} — detail with computed stock summary
- PUT  /api/v1/warehouses/{id} — update fields (admin)
- GET  /api/v1/warehouses/{id}/stock — paginated stock levels
- Non-admin create → 403

All tests run against the real test PostgreSQL database via the async_client
and seeded_db fixtures.  Error assertions use response.json()["error"][...] per
the global http_exception_handler envelope (DEC-001, backend_developer).
"""

import uuid

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# POST /api/v1/warehouses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_warehouse_as_admin(
    async_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Admin can create a warehouse; response is HTTP 201 with full schema."""
    response = await async_client.post(
        "/api/v1/warehouses",
        json={"name": "North Depot", "location": "Building N", "capacity": 750},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "North Depot"
    assert body["location"] == "Building N"
    assert body["capacity"] == 750
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_warehouse_non_admin_returns_403(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """A regular (non-admin) user receives HTTP 403 when attempting to create a warehouse."""
    response = await async_client.post(
        "/api/v1/warehouses",
        json={"name": "Unauthorized Depot", "location": "Building X", "capacity": 100},
        headers=auth_headers,
    )
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# GET /api/v1/warehouses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_warehouses_returns_paginated_envelope(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """GET /warehouses returns the standard paginated envelope with all seeded warehouses."""
    response = await async_client.get("/api/v1/warehouses", headers=seeded_db["user_auth"])
    assert response.status_code == 200, response.text
    body = response.json()

    # Verify pagination envelope shape
    assert "data" in body
    assert "pagination" in body
    pagination = body["pagination"]
    assert "page" in pagination
    assert "per_page" in pagination
    assert "total" in pagination
    assert "total_pages" in pagination


@pytest.mark.asyncio
async def test_list_warehouses_includes_seeded_warehouses(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """List endpoint returns the two seeded warehouses."""
    response = await async_client.get("/api/v1/warehouses", headers=seeded_db["user_auth"])
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total"] == 2
    warehouse_names = {w["name"] for w in body["data"]}
    assert "Main Warehouse" in warehouse_names
    assert "Secondary Warehouse" in warehouse_names


# ---------------------------------------------------------------------------
# GET /api/v1/warehouses/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_warehouse_detail_schema(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Warehouse detail response includes the computed stock summary fields."""
    response = await async_client.get(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()

    # Base warehouse fields
    assert body["id"] == seeded_db["warehouse_id"]
    assert "name" in body
    assert "location" in body
    assert "capacity" in body
    assert "is_active" in body
    assert "created_at" in body
    assert "updated_at" in body

    # Stock summary fields
    assert "total_products" in body
    assert "total_quantity" in body
    assert "capacity_utilization_pct" in body


@pytest.mark.asyncio
async def test_get_warehouse_detail_stock_summary_values(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Stock summary reflects the seeded data: 2 products, total qty 55, correct utilization.

    Seeded data for Main Warehouse (capacity=1000):
      - product1 quantity=50, min_threshold=10
      - product2 quantity=5,  min_threshold=20
    → total_products=2, total_quantity=55, utilization=(55/1000)*100=5.5
    """
    response = await async_client.get(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    body = response.json()

    assert body["total_products"] == 2
    assert body["total_quantity"] == 55
    assert abs(body["capacity_utilization_pct"] - 5.5) < 0.01


@pytest.mark.asyncio
async def test_get_warehouse_detail_not_found(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """A request for a non-existent warehouse ID returns HTTP 404."""
    response = await async_client.get(
        f"/api/v1/warehouses/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# PUT /api/v1/warehouses/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_warehouse_name(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Admin can update the warehouse name; response reflects the change."""
    response = await async_client.put(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}",
        json={"name": "Renamed Warehouse"},
        headers=seeded_db["admin_auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Renamed Warehouse"
    assert body["id"] == seeded_db["warehouse_id"]


@pytest.mark.asyncio
async def test_update_warehouse_capacity(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Admin can update warehouse capacity."""
    response = await async_client.put(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}",
        json={"capacity": 2000},
        headers=seeded_db["admin_auth"],
    )
    assert response.status_code == 200
    assert response.json()["capacity"] == 2000


@pytest.mark.asyncio
async def test_update_warehouse_non_admin_returns_403(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """A regular user receives HTTP 403 when attempting to update a warehouse."""
    response = await async_client.put(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}",
        json={"name": "Unauthorized Update"},
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# GET /api/v1/warehouses/{id}/stock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_warehouse_stock_returns_paginated_envelope(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Warehouse stock endpoint returns a paginated envelope of stock level records."""
    response = await async_client.get(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}/stock",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert "data" in body
    assert "pagination" in body
    assert "page" in body["pagination"]
    assert "per_page" in body["pagination"]
    assert "total" in body["pagination"]
    assert "total_pages" in body["pagination"]


@pytest.mark.asyncio
async def test_get_warehouse_stock_total_matches_seeded_data(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Main Warehouse has 2 stock records (product1 and product2)."""
    response = await async_client.get(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}/stock",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    body = response.json()

    assert body["pagination"]["total"] == 2
    product_ids = {item["product_id"] for item in body["data"]}
    assert seeded_db["product1_id"] in product_ids
    assert seeded_db["product2_id"] in product_ids


@pytest.mark.asyncio
async def test_get_warehouse_stock_item_schema(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Each stock level record in the list includes nested product and warehouse summaries."""
    response = await async_client.get(
        f"/api/v1/warehouses/{seeded_db['warehouse_id']}/stock",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) > 0

    item = items[0]
    assert "id" in item
    assert "product_id" in item
    assert "warehouse_id" in item
    assert "quantity" in item
    assert "min_threshold" in item
    assert "product" in item
    assert "warehouse" in item

    # Nested product summary
    assert "id" in item["product"]
    assert "name" in item["product"]
    assert "sku" in item["product"]

    # Nested warehouse summary
    assert "id" in item["warehouse"]
    assert "name" in item["warehouse"]
    assert "location" in item["warehouse"]


@pytest.mark.asyncio
async def test_get_warehouse_stock_not_found(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Requesting stock for a non-existent warehouse returns HTTP 404."""
    response = await async_client.get(
        f"/api/v1/warehouses/{uuid.uuid4()}/stock",
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
