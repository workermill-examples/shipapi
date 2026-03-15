"""Tests for warehouse endpoints."""

import uuid

from fastapi.testclient import TestClient

from src.models.warehouse import Warehouse


def test_list_warehouses_success(client: TestClient, regular_user_headers: dict[str, str]):
    """Test listing warehouses with pagination."""
    response = client.get("/api/v1/warehouses", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check pagination structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

    # Should have seeded warehouses
    assert data["total"] >= 2  # At least East and West warehouses
    assert len(data["items"]) >= 2

    # Check warehouse structure
    if data["items"]:
        warehouse = data["items"][0]
        assert "id" in warehouse
        assert "name" in warehouse
        assert "code" in warehouse
        assert "address" in warehouse
        assert "is_active" in warehouse
        assert "created_at" in warehouse
        assert "updated_at" in warehouse


def test_list_warehouses_pagination(client: TestClient, regular_user_headers: dict[str, str]):
    """Test warehouse listing pagination."""
    response = client.get("/api/v1/warehouses?page=1&per_page=1", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["per_page"] == 1
    assert len(data["items"]) <= 1


def test_list_warehouses_no_auth(client: TestClient):
    """Test listing warehouses fails without authentication."""
    response = client.get("/api/v1/warehouses")

    assert response.status_code == 401


def test_create_warehouse_success(client: TestClient, admin_headers: dict[str, str]):
    """Test successful warehouse creation."""
    warehouse_data = {"name": "Test Warehouse", "code": "TEST01", "address": "123 Test Street, Test City, TC 12345"}

    response = client.post("/api/v1/warehouses", json=warehouse_data, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == warehouse_data["name"]
    assert data["code"] == warehouse_data["code"]
    assert data["address"] == warehouse_data["address"]
    assert data["is_active"] is True  # Default value
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_warehouse_duplicate_code(client: TestClient, admin_headers: dict[str, str]):
    """Test creating warehouse with duplicate code."""
    # First create a warehouse
    warehouse_data = {"name": "First Warehouse", "code": "UNIQUE01", "address": "123 First Street"}
    response = client.post("/api/v1/warehouses", json=warehouse_data, headers=admin_headers)
    assert response.status_code == 201

    # Try to create another with the same code
    duplicate_data = {
        "name": "Second Warehouse",
        "code": "UNIQUE01",  # Same code
        "address": "456 Second Street",
    }

    response = client.post("/api/v1/warehouses", json=duplicate_data, headers=admin_headers)

    assert response.status_code == 409
    assert "code already exists" in response.json()["detail"]


def test_create_warehouse_validation_errors(client: TestClient, admin_headers: dict[str, str]):
    """Test warehouse creation validation errors."""
    # Empty name
    response = client.post(
        "/api/v1/warehouses", json={"name": "", "code": "TEST02", "address": "123 Test St"}, headers=admin_headers
    )
    assert response.status_code == 422

    # Empty code
    response = client.post(
        "/api/v1/warehouses",
        json={"name": "Test Warehouse", "code": "", "address": "123 Test St"},
        headers=admin_headers,
    )
    assert response.status_code == 422

    # Empty address
    response = client.post(
        "/api/v1/warehouses", json={"name": "Test Warehouse", "code": "TEST03", "address": ""}, headers=admin_headers
    )
    assert response.status_code == 422


def test_create_warehouse_non_admin(client: TestClient, regular_user_headers: dict[str, str]):
    """Test creating warehouse fails for non-admin user."""
    warehouse_data = {"name": "Test Warehouse", "code": "TEST04", "address": "123 Test Street"}

    response = client.post("/api/v1/warehouses", json=warehouse_data, headers=regular_user_headers)

    assert response.status_code == 403


def test_create_warehouse_no_auth(client: TestClient):
    """Test creating warehouse fails without authentication."""
    warehouse_data = {"name": "Test Warehouse", "code": "TEST05", "address": "123 Test Street"}

    response = client.post("/api/v1/warehouses", json=warehouse_data)

    assert response.status_code == 401


def test_get_warehouse_success(
    client: TestClient, regular_user_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test getting a warehouse by ID with stock summary."""
    response = client.get(f"/api/v1/warehouses/{test_warehouse_east.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(test_warehouse_east.id)
    assert data["name"] == test_warehouse_east.name
    assert data["code"] == test_warehouse_east.code
    assert data["address"] == test_warehouse_east.address
    assert data["is_active"] == test_warehouse_east.is_active

    # Should include stock summary
    assert "stock_summary" in data
    if data["stock_summary"]:
        assert "total_items" in data["stock_summary"]
        assert "total_quantity" in data["stock_summary"]
        assert isinstance(data["stock_summary"]["total_items"], int)
        assert isinstance(data["stock_summary"]["total_quantity"], int)


def test_get_warehouse_not_found(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting non-existent warehouse."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/warehouses/{fake_id}", headers=regular_user_headers)

    assert response.status_code == 404
    assert "Warehouse not found" in response.json()["detail"]


def test_get_warehouse_invalid_uuid(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting warehouse with invalid UUID format."""
    response = client.get("/api/v1/warehouses/invalid-uuid", headers=regular_user_headers)

    assert response.status_code == 422  # UUID validation error


def test_update_warehouse_success(client: TestClient, admin_headers: dict[str, str], test_warehouse_east: Warehouse):
    """Test successful warehouse update."""
    update_data = {"name": "Updated Warehouse Name", "address": "456 Updated Street, Updated City, UC 67890"}

    response = client.put(f"/api/v1/warehouses/{test_warehouse_east.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == update_data["name"]
    assert data["address"] == update_data["address"]
    assert data["id"] == str(test_warehouse_east.id)
    assert data["code"] == test_warehouse_east.code  # Should remain unchanged


def test_update_warehouse_partial(client: TestClient, admin_headers: dict[str, str], test_warehouse_east: Warehouse):
    """Test partial warehouse update."""
    update_data = {"is_active": False}

    response = client.put(f"/api/v1/warehouses/{test_warehouse_east.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["is_active"] is False
    assert data["name"] == test_warehouse_east.name  # Should remain unchanged
    assert data["code"] == test_warehouse_east.code  # Should remain unchanged


def test_update_warehouse_duplicate_code(
    client: TestClient, admin_headers: dict[str, str], test_warehouse_east: Warehouse, test_warehouse_west: Warehouse
):
    """Test updating warehouse to use existing code."""
    update_data = {
        "code": test_warehouse_west.code  # Use existing code from another warehouse
    }

    response = client.put(f"/api/v1/warehouses/{test_warehouse_east.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 409
    assert "code already exists" in response.json()["detail"]


def test_update_warehouse_not_found(client: TestClient, admin_headers: dict[str, str]):
    """Test updating non-existent warehouse."""
    fake_id = str(uuid.uuid4())
    update_data = {"name": "Updated Name"}

    response = client.put(f"/api/v1/warehouses/{fake_id}", json=update_data, headers=admin_headers)

    assert response.status_code == 404


def test_update_warehouse_non_admin(
    client: TestClient, regular_user_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test updating warehouse fails for non-admin user."""
    update_data = {"name": "Updated Name"}

    response = client.put(
        f"/api/v1/warehouses/{test_warehouse_east.id}", json=update_data, headers=regular_user_headers
    )

    assert response.status_code == 403


def test_delete_warehouse_success(client: TestClient, admin_headers: dict[str, str], db):
    """Test successful warehouse deletion."""
    # Create a warehouse without stock levels
    warehouse = Warehouse(name="Warehouse to Delete", code="DEL01", address="123 Delete St")
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)

    response = client.delete(f"/api/v1/warehouses/{warehouse.id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["detail"] == "Warehouse deleted successfully"


def test_delete_warehouse_with_stock_levels(
    client: TestClient, admin_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test deleting warehouse with stock levels fails."""
    # The test_warehouse_east should have stock levels from seeded data
    response = client.delete(f"/api/v1/warehouses/{test_warehouse_east.id}", headers=admin_headers)

    assert response.status_code == 400
    assert "Cannot delete warehouse with stock levels" in response.json()["detail"]


def test_delete_warehouse_not_found(client: TestClient, admin_headers: dict[str, str]):
    """Test deleting non-existent warehouse."""
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/warehouses/{fake_id}", headers=admin_headers)

    assert response.status_code == 404


def test_delete_warehouse_non_admin(
    client: TestClient, regular_user_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test deleting warehouse fails for non-admin user."""
    response = client.delete(f"/api/v1/warehouses/{test_warehouse_east.id}", headers=regular_user_headers)

    assert response.status_code == 403


def test_warehouse_stock_summary_calculation(
    client: TestClient, regular_user_headers: dict[str, str], test_warehouse_east: Warehouse
):
    """Test that warehouse detail includes accurate stock summary."""
    response = client.get(f"/api/v1/warehouses/{test_warehouse_east.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Should include stock summary
    assert "stock_summary" in data
    stock_summary = data["stock_summary"]

    # Verify the structure
    assert "total_items" in stock_summary
    assert "total_quantity" in stock_summary

    # Values should be non-negative integers
    assert isinstance(stock_summary["total_items"], int)
    assert isinstance(stock_summary["total_quantity"], int)
    assert stock_summary["total_items"] >= 0
    assert stock_summary["total_quantity"] >= 0

    # For the seeded data, east warehouse should have stock
    assert stock_summary["total_items"] >= 1  # At least one product
    assert stock_summary["total_quantity"] >= 1  # At least some quantity


def test_warehouse_stock_summary_empty_warehouse(client: TestClient, admin_headers: dict[str, str]):
    """Test stock summary for warehouse with no stock levels."""
    # Create a new warehouse with no stock
    warehouse_data = {"name": "Empty Warehouse", "code": "EMPTY01", "address": "123 Empty St"}

    create_response = client.post("/api/v1/warehouses", json=warehouse_data, headers=admin_headers)
    assert create_response.status_code == 201
    warehouse_id = create_response.json()["id"]

    # Get the warehouse detail
    response = client.get(f"/api/v1/warehouses/{warehouse_id}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # Should have stock summary with zero values
    assert "stock_summary" in data
    stock_summary = data["stock_summary"]
    assert stock_summary["total_items"] == 0
    assert stock_summary["total_quantity"] == 0


def test_warehouses_endpoints_have_prefix(client: TestClient, admin_headers: dict[str, str]):
    """Test all warehouse endpoints are under /api/v1/warehouses prefix."""
    # Should work
    response = client.get("/api/v1/warehouses", headers=admin_headers)
    assert response.status_code == 200

    # Should not work (wrong prefix)
    response = client.get("/warehouses", headers=admin_headers)
    assert response.status_code == 404
