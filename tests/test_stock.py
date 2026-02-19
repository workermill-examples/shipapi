"""Integration tests for stock management endpoints.

Covers:
- PUT  /api/v1/stock/{product_id}/{warehouse_id} — create new stock level
- PUT  /api/v1/stock/{product_id}/{warehouse_id} — update existing stock level
- POST /api/v1/stock/transfer — atomic transfer (source decremented, destination
  incremented, transfer record created)
- POST /api/v1/stock/transfer — insufficient stock → 400, no partial update
- POST /api/v1/stock/transfer — same-warehouse transfer → 422 (Pydantic validation)
- GET  /api/v1/stock/alerts   — products below min_threshold

Seeded data (from conftest.seeded_db):
  Main Warehouse     (warehouse_id,  capacity=1000):
    product1 qty=50 min_threshold=10  (sufficient for transfers)
    product2 qty=5  min_threshold=20  (below threshold → appears in alerts)
  Secondary Warehouse (warehouse2_id, capacity=500):
    product3 qty=100 min_threshold=15

All tests run against the real test PostgreSQL database.
Error assertions use response.json()["error"]["..."] per the project's
ErrorResponse envelope (DEC-001, backend_developer).
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _find_stock_in_warehouse(
    async_client: AsyncClient,
    warehouse_id: str,
    product_id: str,
    headers: dict[str, str],
) -> dict | None:
    """Return the stock level record for a product in a warehouse, or None."""
    resp = await async_client.get(
        f"/api/v1/warehouses/{warehouse_id}/stock",
        headers=headers,
        params={"per_page": 100},
    )
    assert resp.status_code == 200, f"Failed to list warehouse stock: {resp.text}"
    for item in resp.json()["data"]:
        if item["product_id"] == product_id:
            return item
    return None


# ---------------------------------------------------------------------------
# PUT /api/v1/stock/{product_id}/{warehouse_id} — upsert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_stock_creates_new_record(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """PUT creates a new stock level when the (product, warehouse) pair does not exist.

    product3 exists only in warehouse2 in the seeded data; creating it in
    warehouse1 should return HTTP 200 with the requested quantity.
    """
    response = await async_client.put(
        f"/api/v1/stock/{seeded_db['product3_id']}/{seeded_db['warehouse_id']}",
        json={"quantity": 25, "min_threshold": 5},
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["quantity"] == 25
    assert body["min_threshold"] == 5
    assert body["product_id"] == seeded_db["product3_id"]
    assert body["warehouse_id"] == seeded_db["warehouse_id"]

    # Nested relationships present in response
    assert body["product"]["id"] == seeded_db["product3_id"]
    assert body["warehouse"]["id"] == seeded_db["warehouse_id"]


@pytest.mark.asyncio
async def test_update_stock_creates_record_with_default_threshold(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """When min_threshold is omitted, the new record uses the default value of 10."""
    response = await async_client.put(
        f"/api/v1/stock/{seeded_db['product3_id']}/{seeded_db['warehouse_id']}",
        json={"quantity": 30},
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    assert response.json()["min_threshold"] == 10


@pytest.mark.asyncio
async def test_update_stock_updates_existing_record(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """PUT updates quantity on an existing (product, warehouse) record.

    product1 in warehouse1 is seeded with quantity=50.  Updating to 75
    should return the new value.
    """
    response = await async_client.put(
        f"/api/v1/stock/{seeded_db['product1_id']}/{seeded_db['warehouse_id']}",
        json={"quantity": 75},
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["quantity"] == 75
    # min_threshold should be unchanged (still 10)
    assert body["min_threshold"] == 10


@pytest.mark.asyncio
async def test_update_stock_updates_threshold_on_existing(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """PUT can also update min_threshold on an existing record."""
    response = await async_client.put(
        f"/api/v1/stock/{seeded_db['product1_id']}/{seeded_db['warehouse_id']}",
        json={"quantity": 50, "min_threshold": 25},
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    assert response.json()["min_threshold"] == 25


@pytest.mark.asyncio
async def test_update_stock_nonexistent_product_returns_404(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Referencing a non-existent product returns HTTP 404."""
    import uuid

    response = await async_client.put(
        f"/api/v1/stock/{uuid.uuid4()}/{seeded_db['warehouse_id']}",
        json={"quantity": 10},
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_update_stock_nonexistent_warehouse_returns_404(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Referencing a non-existent warehouse returns HTTP 404."""
    import uuid

    response = await async_client.put(
        f"/api/v1/stock/{seeded_db['product1_id']}/{uuid.uuid4()}",
        json={"quantity": 10},
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /api/v1/stock/transfer — atomic transfer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_transfer_decrements_source(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Transferring stock decrements the source warehouse quantity.

    product1 starts at 50 in warehouse1; after transferring 20 it should be 30.
    """
    await async_client.post(
        "/api/v1/stock/transfer",
        json={
            "product_id": seeded_db["product1_id"],
            "from_warehouse_id": seeded_db["warehouse_id"],
            "to_warehouse_id": seeded_db["warehouse2_id"],
            "quantity": 20,
        },
        headers=seeded_db["user_auth"],
    )

    source_item = await _find_stock_in_warehouse(
        async_client, seeded_db["warehouse_id"], seeded_db["product1_id"], seeded_db["user_auth"]
    )
    assert source_item is not None, "product1 stock record missing from warehouse1 after transfer"
    assert source_item["quantity"] == 30


@pytest.mark.asyncio
async def test_atomic_transfer_increments_destination(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Transferring stock increments (or creates) the destination warehouse record.

    product1 has no stock in warehouse2 initially; after transferring 20 from
    warehouse1, warehouse2 should have product1 at quantity=20.
    """
    await async_client.post(
        "/api/v1/stock/transfer",
        json={
            "product_id": seeded_db["product1_id"],
            "from_warehouse_id": seeded_db["warehouse_id"],
            "to_warehouse_id": seeded_db["warehouse2_id"],
            "quantity": 20,
        },
        headers=seeded_db["user_auth"],
    )

    dest_item = await _find_stock_in_warehouse(
        async_client, seeded_db["warehouse2_id"], seeded_db["product1_id"], seeded_db["user_auth"]
    )
    assert dest_item is not None, "product1 stock record missing from warehouse2 after transfer"
    assert dest_item["quantity"] == 20


@pytest.mark.asyncio
async def test_atomic_transfer_creates_transfer_record(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """A successful transfer returns HTTP 201 with the transfer record fields."""
    response = await async_client.post(
        "/api/v1/stock/transfer",
        json={
            "product_id": seeded_db["product1_id"],
            "from_warehouse_id": seeded_db["warehouse_id"],
            "to_warehouse_id": seeded_db["warehouse2_id"],
            "quantity": 15,
            "notes": "Test transfer",
        },
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["product_id"] == seeded_db["product1_id"]
    assert body["from_warehouse_id"] == seeded_db["warehouse_id"]
    assert body["to_warehouse_id"] == seeded_db["warehouse2_id"]
    assert body["quantity"] == 15
    assert body["notes"] == "Test transfer"
    assert "id" in body
    assert "initiated_by" in body
    assert "created_at" in body


# ---------------------------------------------------------------------------
# POST /api/v1/stock/transfer — failure cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insufficient_stock_transfer_returns_400(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Transferring more than available stock returns HTTP 400 with INSUFFICIENT_STOCK.

    product2 in warehouse1 has quantity=5; attempting to transfer 100 must fail.
    """
    response = await async_client.post(
        "/api/v1/stock/transfer",
        json={
            "product_id": seeded_db["product2_id"],
            "from_warehouse_id": seeded_db["warehouse_id"],
            "to_warehouse_id": seeded_db["warehouse2_id"],
            "quantity": 100,
        },
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 400, response.text
    body = response.json()
    assert "INSUFFICIENT_STOCK" in body["error"]["message"]


@pytest.mark.asyncio
async def test_insufficient_stock_transfer_no_partial_update(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """A failed transfer (insufficient stock) leaves both warehouses unchanged.

    product2 starts at qty=5 in warehouse1 and has no record in warehouse2.
    After the failed transfer attempt of 100, source must still be 5 and
    warehouse2 must still have no record for product2.
    """
    # Attempt the failing transfer
    resp = await async_client.post(
        "/api/v1/stock/transfer",
        json={
            "product_id": seeded_db["product2_id"],
            "from_warehouse_id": seeded_db["warehouse_id"],
            "to_warehouse_id": seeded_db["warehouse2_id"],
            "quantity": 100,
        },
        headers=seeded_db["user_auth"],
    )
    assert resp.status_code == 400

    # Source warehouse: product2 quantity must be unchanged at 5
    source_item = await _find_stock_in_warehouse(
        async_client, seeded_db["warehouse_id"], seeded_db["product2_id"], seeded_db["user_auth"]
    )
    assert source_item is not None, "product2 stock record missing from source warehouse"
    assert source_item["quantity"] == 5, (
        f"Source quantity was modified despite failed transfer: {source_item['quantity']}"
    )

    # Destination warehouse: product2 must NOT be present (no partial creation)
    dest_item = await _find_stock_in_warehouse(
        async_client,
        seeded_db["warehouse2_id"],
        seeded_db["product2_id"],
        seeded_db["user_auth"],
    )
    assert dest_item is None, (
        f"Destination received a partial stock record despite failed transfer: {dest_item}"
    )


@pytest.mark.asyncio
async def test_same_warehouse_transfer_returns_422(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Sending the same warehouse for source and destination is rejected by Pydantic (422)."""
    response = await async_client.post(
        "/api/v1/stock/transfer",
        json={
            "product_id": seeded_db["product1_id"],
            "from_warehouse_id": seeded_db["warehouse_id"],
            "to_warehouse_id": seeded_db["warehouse_id"],  # same as source
            "quantity": 10,
        },
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "UNPROCESSABLE_ENTITY"


# ---------------------------------------------------------------------------
# GET /api/v1/stock/alerts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stock_alerts_returns_paginated_envelope(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """GET /stock/alerts returns the standard paginated envelope."""
    response = await async_client.get(
        "/api/v1/stock/alerts",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert "data" in body
    assert "pagination" in body
    assert "total" in body["pagination"]


@pytest.mark.asyncio
async def test_stock_alerts_includes_below_threshold_product(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """product2 (qty=5, min_threshold=20) appears in the alerts list.

    Seeded deliberately to trigger this test: deficit = 20 - 5 = 15.
    """
    response = await async_client.get(
        "/api/v1/stock/alerts",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    body = response.json()

    assert body["pagination"]["total"] >= 1

    alert_product_ids = [alert["product"]["id"] for alert in body["data"]]
    assert seeded_db["product2_id"] in alert_product_ids, (
        f"product2 not found in alerts: {alert_product_ids}"
    )


@pytest.mark.asyncio
async def test_stock_alerts_item_schema(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Each alert record includes product, warehouse, quantity, min_threshold, and deficit."""
    response = await async_client.get(
        "/api/v1/stock/alerts",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    alerts = response.json()["data"]
    assert len(alerts) > 0

    alert = alerts[0]
    assert "product" in alert
    assert "warehouse" in alert
    assert "quantity" in alert
    assert "min_threshold" in alert
    assert "deficit" in alert
    assert alert["deficit"] == alert["min_threshold"] - alert["quantity"]


@pytest.mark.asyncio
async def test_stock_alerts_product2_deficit(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """product2 alert has the correct deficit value: min_threshold(20) - quantity(5) = 15."""
    response = await async_client.get(
        "/api/v1/stock/alerts",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    alerts = response.json()["data"]

    product2_alert = next(
        (a for a in alerts if a["product"]["id"] == seeded_db["product2_id"]), None
    )
    assert product2_alert is not None, "product2 not found in alerts"
    assert product2_alert["quantity"] == 5
    assert product2_alert["min_threshold"] == 20
    assert product2_alert["deficit"] == 15


@pytest.mark.asyncio
async def test_stock_alerts_excludes_above_threshold_products(
    async_client: AsyncClient,
    seeded_db: dict,
) -> None:
    """Products with quantity >= min_threshold do not appear in the alerts list.

    product1 (qty=50, min_threshold=10) and product3 (qty=100, min_threshold=15)
    are both above their thresholds.
    """
    response = await async_client.get(
        "/api/v1/stock/alerts",
        headers=seeded_db["user_auth"],
    )
    assert response.status_code == 200
    alert_product_ids = {a["product"]["id"] for a in response.json()["data"]}

    assert seeded_db["product1_id"] not in alert_product_ids, (
        "product1 (qty=50 > threshold=10) should not appear in alerts"
    )
    assert seeded_db["product3_id"] not in alert_product_ids, (
        "product3 (qty=100 > threshold=15) should not appear in alerts"
    )
