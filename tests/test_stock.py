"""Tests for stock management endpoints."""

import uuid

from fastapi.testclient import TestClient

from src.models.product import Product
from src.models.warehouse import Warehouse


def test_list_stock_levels_success(client: TestClient, regular_user_headers: dict[str, str]):
    """Test listing stock levels with pagination."""
    response = client.get("/api/v1/stock", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check pagination structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

    # Should have seeded stock levels
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    # Check stock level structure
    if data["items"]:
        stock = data["items"][0]
        assert "id" in stock
        assert "product_id" in stock
        assert "warehouse_id" in stock
        assert "quantity" in stock
        assert "low_stock_threshold" in stock
        assert "created_at" in stock
        assert "updated_at" in stock


def test_list_stock_levels_filter_by_warehouse(
    client: TestClient, regular_user_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test filtering stock levels by warehouse."""
    response = client.get(f"/api/v1/stock?warehouse_id={test_warehouse_east.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned items should belong to the specified warehouse
    for stock in data["items"]:
        assert stock["warehouse_id"] == str(test_warehouse_east.id)


def test_list_stock_levels_filter_by_product(
    client: TestClient, regular_user_headers: dict[str, str], test_product: Product
):
    """Test filtering stock levels by product."""
    response = client.get(f"/api/v1/stock?product_id={test_product.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned items should be for the specified product
    for stock in data["items"]:
        assert stock["product_id"] == str(test_product.id)


def test_list_stock_levels_no_auth(client: TestClient):
    """Test listing stock levels fails without authentication."""
    response = client.get("/api/v1/stock")

    assert response.status_code == 401


def test_get_low_stock_alerts(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting low stock alerts."""
    response = client.get("/api/v1/stock/alerts", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

    # All returned items should have quantity < low_stock_threshold
    for stock in data["items"]:
        assert stock["quantity"] < stock["low_stock_threshold"]


def test_adjust_stock_create_new(
    client: TestClient, admin_headers: dict[str, str], test_product: Product, test_warehouse_east: Warehouse, db
):
    """Test stock adjustment creates new stock level."""
    # Use a different product/warehouse combination that doesn't exist
    # First, create a new product for this test
    from src.models.product import Product

    new_product = Product(
        name="New Test Product",
        sku="NEW-TEST-001",
        description="Product for stock test",
        price=19.99,
        category_id=test_product.category_id,  # Use existing category
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    adjust_data = {
        "product_id": str(new_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": 50,
        "low_stock_threshold": 5,
    }

    response = client.put("/api/v1/stock/adjust", json=adjust_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["product_id"] == str(new_product.id)
    assert data["warehouse_id"] == str(test_warehouse_east.id)
    assert data["quantity"] == 50
    assert data["low_stock_threshold"] == 5


def test_adjust_stock_update_existing(
    client: TestClient, admin_headers: dict[str, str], test_product: Product, test_warehouse_east: Warehouse
):
    """Test stock adjustment updates existing stock level."""
    adjust_data = {
        "product_id": str(test_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": 200,  # Update to new quantity
        "low_stock_threshold": 15,
    }

    response = client.put("/api/v1/stock/adjust", json=adjust_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["product_id"] == str(test_product.id)
    assert data["warehouse_id"] == str(test_warehouse_east.id)
    assert data["quantity"] == 200
    assert data["low_stock_threshold"] == 15


def test_adjust_stock_invalid_product(
    client: TestClient, admin_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test stock adjustment with invalid product ID."""
    adjust_data = {
        "product_id": str(uuid.uuid4()),  # Non-existent product
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": 50,
        "low_stock_threshold": 5,
    }

    response = client.put("/api/v1/stock/adjust", json=adjust_data, headers=admin_headers)

    assert response.status_code == 404
    assert "Product not found" in response.json()["detail"]


def test_adjust_stock_invalid_warehouse(client: TestClient, admin_headers: dict[str, str], test_product: Product):
    """Test stock adjustment with invalid warehouse ID."""
    adjust_data = {
        "product_id": str(test_product.id),
        "warehouse_id": str(uuid.uuid4()),  # Non-existent warehouse
        "quantity": 50,
        "low_stock_threshold": 5,
    }

    response = client.put("/api/v1/stock/adjust", json=adjust_data, headers=admin_headers)

    assert response.status_code == 404
    assert "Warehouse not found" in response.json()["detail"]


def test_adjust_stock_negative_quantity(
    client: TestClient, admin_headers: dict[str, str], test_product: Product, test_warehouse_east: Warehouse
):
    """Test stock adjustment with negative quantity fails validation."""
    adjust_data = {
        "product_id": str(test_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": -10,  # Negative quantity
        "low_stock_threshold": 5,
    }

    response = client.put("/api/v1/stock/adjust", json=adjust_data, headers=admin_headers)

    assert response.status_code == 422  # Validation error


def test_adjust_stock_non_admin(
    client: TestClient, regular_user_headers: dict[str, str], test_product: Product, test_warehouse_east: Warehouse
):
    """Test stock adjustment fails for non-admin user."""
    adjust_data = {
        "product_id": str(test_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": 50,
        "low_stock_threshold": 5,
    }

    response = client.put("/api/v1/stock/adjust", json=adjust_data, headers=regular_user_headers)

    assert response.status_code == 403


def test_create_stock_transfer_success(
    client: TestClient,
    regular_user_headers: dict[str, str],
    test_product: Product,
    test_warehouse_east: Warehouse,
    test_warehouse_west: Warehouse,
):
    """Test successful stock transfer between warehouses."""
    # First, ensure there's enough stock at the source
    adjust_data = {
        "product_id": str(test_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": 100,
        "low_stock_threshold": 10,
    }
    client.put(
        "/api/v1/stock/adjust",
        json=adjust_data,
        headers={"Authorization": "Bearer " + regular_user_headers["Authorization"].split()[1]},
    )

    transfer_data = {
        "product_id": str(test_product.id),
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(test_warehouse_west.id),
        "quantity": 30,
        "notes": "Test transfer",
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)

    assert response.status_code == 201
    data = response.json()

    assert data["product_id"] == str(test_product.id)
    assert data["from_warehouse_id"] == str(test_warehouse_east.id)
    assert data["to_warehouse_id"] == str(test_warehouse_west.id)
    assert data["quantity"] == 30
    assert data["notes"] == "Test transfer"
    assert "id" in data
    assert "created_at" in data


def test_create_stock_transfer_same_warehouse(
    client: TestClient, regular_user_headers: dict[str, str], test_product: Product, test_warehouse_east: Warehouse
):
    """Test stock transfer fails when source and destination are the same."""
    transfer_data = {
        "product_id": str(test_product.id),
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(test_warehouse_east.id),  # Same as source
        "quantity": 30,
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)

    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]


def test_create_stock_transfer_insufficient_stock(
    client: TestClient,
    regular_user_headers: dict[str, str],
    test_product: Product,
    test_warehouse_east: Warehouse,
    test_warehouse_west: Warehouse,
):
    """Test stock transfer fails with insufficient stock."""
    # Set low stock at source
    adjust_data = {
        "product_id": str(test_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": 5,
        "low_stock_threshold": 10,
    }
    admin_token = regular_user_headers["Authorization"].replace("Bearer ", "")

    # Get admin headers for stock adjustment
    from src.auth import create_access_token

    admin_token = create_access_token(data={"sub": "11111111-1111-1111-1111-111111111111"})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.put("/api/v1/stock/adjust", json=adjust_data, headers=admin_headers)

    # Try to transfer more than available
    transfer_data = {
        "product_id": str(test_product.id),
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(test_warehouse_west.id),
        "quantity": 10,  # More than the 5 available
        "notes": "Should fail",
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)

    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]


def test_create_stock_transfer_no_source_stock(
    client: TestClient,
    regular_user_headers: dict[str, str],
    test_warehouse_east: Warehouse,
    test_warehouse_west: Warehouse,
    db,
):
    """Test stock transfer fails when no stock exists at source."""
    # Create a new product with no stock levels
    from src.models.product import Product

    new_product = Product(
        name="No Stock Product",
        sku="NO-STOCK-001",
        description="Product with no stock",
        price=29.99,
        category_id=str(uuid.UUID("44444444-4444-4444-4444-444444444444")),  # Use seeded category
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    transfer_data = {
        "product_id": str(new_product.id),
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(test_warehouse_west.id),
        "quantity": 10,
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)

    assert response.status_code == 400
    assert "No stock available" in response.json()["detail"]


def test_create_stock_transfer_invalid_product(
    client: TestClient,
    regular_user_headers: dict[str, str],
    test_warehouse_east: Warehouse,
    test_warehouse_west: Warehouse,
):
    """Test stock transfer with invalid product ID."""
    transfer_data = {
        "product_id": str(uuid.uuid4()),  # Non-existent product
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(test_warehouse_west.id),
        "quantity": 10,
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)

    assert response.status_code == 404
    assert "Product not found" in response.json()["detail"]


def test_create_stock_transfer_invalid_warehouse(
    client: TestClient, regular_user_headers: dict[str, str], test_product: Product, test_warehouse_east: Warehouse
):
    """Test stock transfer with invalid warehouse ID."""
    transfer_data = {
        "product_id": str(test_product.id),
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(uuid.uuid4()),  # Non-existent warehouse
        "quantity": 10,
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)

    assert response.status_code == 404
    assert "Destination warehouse not found" in response.json()["detail"]


def test_get_transfer_history(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting stock transfer history."""
    response = client.get("/api/v1/stock/transfers", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

    # Should have seeded transfers
    assert data["total"] >= 1

    # Check transfer structure
    if data["items"]:
        transfer = data["items"][0]
        assert "id" in transfer
        assert "product_id" in transfer
        assert "from_warehouse_id" in transfer
        assert "to_warehouse_id" in transfer
        assert "quantity" in transfer
        assert "created_at" in transfer


def test_get_transfer_history_filter_by_product(
    client: TestClient, regular_user_headers: dict[str, str], test_product: Product
):
    """Test filtering transfer history by product."""
    response = client.get(f"/api/v1/stock/transfers?product_id={test_product.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned transfers should be for the specified product
    for transfer in data["items"]:
        assert transfer["product_id"] == str(test_product.id)


def test_get_transfer_history_filter_by_warehouse(
    client: TestClient, regular_user_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test filtering transfer history by warehouse."""
    response = client.get(
        f"/api/v1/stock/transfers?warehouse_id={test_warehouse_east.id}", headers=regular_user_headers
    )

    assert response.status_code == 200
    data = response.json()

    # All returned transfers should involve the specified warehouse
    for transfer in data["items"]:
        assert transfer["from_warehouse_id"] == str(test_warehouse_east.id) or transfer["to_warehouse_id"] == str(
            test_warehouse_east.id
        )


def test_stock_transfer_atomicity(
    client: TestClient,
    regular_user_headers: dict[str, str],
    test_product: Product,
    test_warehouse_east: Warehouse,
    test_warehouse_west: Warehouse,
    admin_headers: dict[str, str],
):
    """Test that stock transfers are atomic (all or nothing)."""
    # Set initial stock levels
    initial_stock_east = 50
    initial_stock_west = 20

    # Set stock at east warehouse
    adjust_east = {
        "product_id": str(test_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": initial_stock_east,
        "low_stock_threshold": 10,
    }
    client.put("/api/v1/stock/adjust", json=adjust_east, headers=admin_headers)

    # Set stock at west warehouse
    adjust_west = {
        "product_id": str(test_product.id),
        "warehouse_id": str(test_warehouse_west.id),
        "quantity": initial_stock_west,
        "low_stock_threshold": 10,
    }
    client.put("/api/v1/stock/adjust", json=adjust_west, headers=admin_headers)

    # Perform transfer
    transfer_quantity = 15
    transfer_data = {
        "product_id": str(test_product.id),
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(test_warehouse_west.id),
        "quantity": transfer_quantity,
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)
    assert response.status_code == 201

    # Verify quantities were updated correctly
    east_stock_response = client.get(
        f"/api/v1/stock?warehouse_id={test_warehouse_east.id}&product_id={test_product.id}",
        headers=regular_user_headers,
    )
    west_stock_response = client.get(
        f"/api/v1/stock?warehouse_id={test_warehouse_west.id}&product_id={test_product.id}",
        headers=regular_user_headers,
    )

    east_stock = east_stock_response.json()["items"][0]["quantity"]
    west_stock = west_stock_response.json()["items"][0]["quantity"]

    assert east_stock == initial_stock_east - transfer_quantity
    assert west_stock == initial_stock_west + transfer_quantity


def test_stock_endpoints_have_prefix(client: TestClient, admin_headers: dict[str, str]):
    """Test all stock endpoints are under /api/v1/stock prefix."""
    # Should work
    response = client.get("/api/v1/stock", headers=admin_headers)
    assert response.status_code == 200

    # Should not work (wrong prefix)
    response = client.get("/stock", headers=admin_headers)
    assert response.status_code == 404


def test_stock_transfer_creates_destination_if_missing(
    client: TestClient,
    regular_user_headers: dict[str, str],
    test_warehouse_east: Warehouse,
    admin_headers: dict[str, str],
    db,
):
    """Test that stock transfer creates destination stock level if it doesn't exist."""
    # Create a new warehouse with no stock levels
    from src.models.warehouse import Warehouse

    new_warehouse = Warehouse(name="New Test Warehouse", code="NEW01", address="123 New St")
    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)

    # Create a new product
    from src.models.product import Product

    new_product = Product(
        name="Transfer Test Product",
        sku="TRANSFER-001",
        description="Product for transfer test",
        price=39.99,
        category_id=str(uuid.UUID("44444444-4444-4444-4444-444444444444")),
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # Set stock at source warehouse
    adjust_data = {
        "product_id": str(new_product.id),
        "warehouse_id": str(test_warehouse_east.id),
        "quantity": 100,
        "low_stock_threshold": 10,
    }
    client.put("/api/v1/stock/adjust", json=adjust_data, headers=admin_headers)

    # Transfer to new warehouse (which has no stock level for this product)
    transfer_data = {
        "product_id": str(new_product.id),
        "from_warehouse_id": str(test_warehouse_east.id),
        "to_warehouse_id": str(new_warehouse.id),
        "quantity": 25,
    }

    response = client.post("/api/v1/stock/transfers", json=transfer_data, headers=regular_user_headers)

    assert response.status_code == 201

    # Verify destination stock level was created
    dest_response = client.get(
        f"/api/v1/stock?warehouse_id={new_warehouse.id}&product_id={new_product.id}", headers=regular_user_headers
    )
    assert dest_response.status_code == 200
    dest_data = dest_response.json()
    assert len(dest_data["items"]) == 1
    assert dest_data["items"][0]["quantity"] == 25
