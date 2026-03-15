"""Tests for product endpoints."""

import uuid

from fastapi.testclient import TestClient

from src.models.category import Category
from src.models.product import Product


def test_list_products_success(client: TestClient, regular_user_headers: dict[str, str]):
    """Test listing products with pagination."""
    response = client.get("/api/v1/products", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check pagination structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

    # Should have seeded products
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    # Check product structure
    if data["items"]:
        product = data["items"][0]
        assert "id" in product
        assert "name" in product
        assert "sku" in product
        assert "description" in product
        assert "price" in product
        assert "is_active" in product
        assert "category_id" in product
        assert "created_at" in product
        assert "updated_at" in product


def test_list_products_pagination(client: TestClient, regular_user_headers: dict[str, str]):
    """Test product listing pagination."""
    response = client.get("/api/v1/products?page=1&per_page=1", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["per_page"] == 1
    assert len(data["items"]) <= 1


def test_list_products_filter_by_category(
    client: TestClient, regular_user_headers: dict[str, str], test_category: Category
):
    """Test filtering products by category."""
    response = client.get(f"/api/v1/products?category_id={test_category.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned products should belong to the specified category
    for product in data["items"]:
        assert product["category_id"] == str(test_category.id)


def test_list_products_filter_by_price_range(client: TestClient, regular_user_headers: dict[str, str]):
    """Test filtering products by price range."""
    response = client.get("/api/v1/products?min_price=20&max_price=30", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned products should be within price range
    for product in data["items"]:
        assert 20 <= product["price"] <= 30


def test_list_products_filter_by_active_status(client: TestClient, regular_user_headers: dict[str, str]):
    """Test filtering products by active status."""
    # Test active products
    response = client.get("/api/v1/products?is_active=true", headers=regular_user_headers)
    assert response.status_code == 200
    active_data = response.json()

    for product in active_data["items"]:
        assert product["is_active"] is True

    # Test inactive products
    response = client.get("/api/v1/products?is_active=false", headers=regular_user_headers)
    assert response.status_code == 200
    inactive_data = response.json()

    for product in inactive_data["items"]:
        assert product["is_active"] is False


def test_list_products_search(client: TestClient, regular_user_headers: dict[str, str]):
    """Test full-text search on products."""
    # Search for 'temperature' which should match the seeded product
    response = client.get("/api/v1/products?search=temperature", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Should find at least one product
    assert data["total"] >= 1
    # Results should be ordered by relevance when searching


def test_list_products_sort_by_name(client: TestClient, regular_user_headers: dict[str, str]):
    """Test sorting products by name."""
    response = client.get("/api/v1/products?sort_by=name", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check if products are sorted by name (case insensitive)
    if len(data["items"]) > 1:
        names = [product["name"].lower() for product in data["items"]]
        assert names == sorted(names)


def test_list_products_sort_by_price(client: TestClient, regular_user_headers: dict[str, str]):
    """Test sorting products by price."""
    response = client.get("/api/v1/products?sort_by=price", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check if products are sorted by price
    if len(data["items"]) > 1:
        prices = [product["price"] for product in data["items"]]
        assert prices == sorted(prices)


def test_list_products_no_auth(client: TestClient):
    """Test listing products fails without authentication."""
    response = client.get("/api/v1/products")

    assert response.status_code == 401


def test_create_product_success(client: TestClient, admin_headers: dict[str, str], test_category: Category):
    """Test successful product creation."""
    product_data = {
        "name": "Test Product",
        "sku": "TEST-001",
        "description": "A test product for unit testing",
        "price": 29.99,
        "category_id": str(test_category.id),
    }

    response = client.post("/api/v1/products", json=product_data, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == product_data["name"]
    assert data["sku"] == product_data["sku"]
    assert data["description"] == product_data["description"]
    assert data["price"] == product_data["price"]
    assert data["category_id"] == str(test_category.id)
    assert data["is_active"] is True  # Default value
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_product_invalid_category(client: TestClient, admin_headers: dict[str, str]):
    """Test creating product with invalid category ID."""
    product_data = {
        "name": "Test Product",
        "sku": "TEST-002",
        "description": "A test product",
        "price": 29.99,
        "category_id": str(uuid.uuid4()),  # Non-existent UUID
    }

    response = client.post("/api/v1/products", json=product_data, headers=admin_headers)

    assert response.status_code == 400
    assert "Category not found" in response.json()["detail"]


def test_create_product_duplicate_sku(client: TestClient, admin_headers: dict[str, str], test_category: Category):
    """Test creating product with duplicate SKU."""
    # First create a product
    product_data = {
        "name": "First Product",
        "sku": "DUPLICATE-SKU",
        "description": "First product",
        "price": 29.99,
        "category_id": str(test_category.id),
    }
    response = client.post("/api/v1/products", json=product_data, headers=admin_headers)
    assert response.status_code == 201

    # Try to create another with the same SKU
    duplicate_data = {
        "name": "Second Product",
        "sku": "DUPLICATE-SKU",
        "description": "Duplicate SKU product",
        "price": 39.99,
        "category_id": str(test_category.id),
    }

    response = client.post("/api/v1/products", json=duplicate_data, headers=admin_headers)

    assert response.status_code == 409
    assert "SKU already exists" in response.json()["detail"]


def test_create_product_invalid_price(client: TestClient, admin_headers: dict[str, str], test_category: Category):
    """Test creating product with invalid price."""
    product_data = {
        "name": "Test Product",
        "sku": "TEST-003",
        "description": "A test product",
        "price": -10.0,  # Negative price should fail
        "category_id": str(test_category.id),
    }

    response = client.post("/api/v1/products", json=product_data, headers=admin_headers)

    assert response.status_code == 422  # Validation error


def test_create_product_non_admin(client: TestClient, regular_user_headers: dict[str, str], test_category: Category):
    """Test creating product fails for non-admin user."""
    product_data = {
        "name": "Test Product",
        "sku": "TEST-004",
        "description": "A test product",
        "price": 29.99,
        "category_id": str(test_category.id),
    }

    response = client.post("/api/v1/products", json=product_data, headers=regular_user_headers)

    assert response.status_code == 403


def test_get_product_success(client: TestClient, regular_user_headers: dict[str, str], test_product: Product):
    """Test getting a product by ID."""
    response = client.get(f"/api/v1/products/{test_product.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(test_product.id)
    assert data["name"] == test_product.name
    assert data["sku"] == test_product.sku
    assert data["description"] == test_product.description
    assert data["price"] == float(test_product.price)
    assert data["is_active"] == test_product.is_active
    assert data["category_id"] == str(test_product.category_id)


def test_get_product_not_found(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting non-existent product."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/products/{fake_id}", headers=regular_user_headers)

    assert response.status_code == 404
    assert "Product not found" in response.json()["detail"]


def test_get_product_invalid_uuid(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting product with invalid UUID format."""
    response = client.get("/api/v1/products/invalid-uuid", headers=regular_user_headers)

    assert response.status_code == 422  # UUID validation error


def test_update_product_success(client: TestClient, admin_headers: dict[str, str], test_product: Product):
    """Test successful product update."""
    update_data = {"name": "Updated Product Name", "description": "Updated description", "price": 39.99}

    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["price"] == update_data["price"]
    assert data["id"] == str(test_product.id)
    assert data["sku"] == test_product.sku  # Should remain unchanged


def test_update_product_partial(client: TestClient, admin_headers: dict[str, str], test_product: Product):
    """Test partial product update."""
    update_data = {"price": 49.99}

    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["price"] == update_data["price"]
    assert data["name"] == test_product.name  # Should remain unchanged
    assert data["description"] == test_product.description  # Should remain unchanged


def test_update_product_invalid_category(client: TestClient, admin_headers: dict[str, str], test_product: Product):
    """Test updating product with invalid category ID."""
    update_data = {"category_id": str(uuid.uuid4())}

    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 400
    assert "Category not found" in response.json()["detail"]


def test_update_product_not_found(client: TestClient, admin_headers: dict[str, str]):
    """Test updating non-existent product."""
    fake_id = str(uuid.uuid4())
    update_data = {"name": "Updated Name"}

    response = client.put(f"/api/v1/products/{fake_id}", json=update_data, headers=admin_headers)

    assert response.status_code == 404


def test_update_product_non_admin(client: TestClient, regular_user_headers: dict[str, str], test_product: Product):
    """Test updating product fails for non-admin user."""
    update_data = {"name": "Updated Name"}

    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data, headers=regular_user_headers)

    assert response.status_code == 403


def test_delete_product_success(client: TestClient, admin_headers: dict[str, str], test_product: Product):
    """Test successful product soft-deletion."""
    response = client.delete(f"/api/v1/products/{test_product.id}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # Should return the updated product
    assert data["id"] == str(test_product.id)
    assert data["is_active"] is False  # Should be soft-deleted

    # Verify the product is marked as inactive
    get_response = client.get(f"/api/v1/products/{test_product.id}", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False


def test_delete_product_not_found(client: TestClient, admin_headers: dict[str, str]):
    """Test deleting non-existent product."""
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/products/{fake_id}", headers=admin_headers)

    assert response.status_code == 404


def test_delete_product_non_admin(client: TestClient, regular_user_headers: dict[str, str], test_product: Product):
    """Test deleting product fails for non-admin user."""
    response = client.delete(f"/api/v1/products/{test_product.id}", headers=regular_user_headers)

    assert response.status_code == 403


def test_product_search_functionality(
    client: TestClient, regular_user_headers: dict[str, str], admin_headers: dict[str, str], test_category: Category
):
    """Test full-text search functionality in detail."""
    # Create a product with specific searchable content
    product_data = {
        "name": "Digital Thermometer Sensor",
        "sku": "SEARCH-TEST-001",
        "description": "High accuracy digital temperature measurement device for industrial applications",
        "price": 35.99,
        "category_id": str(test_category.id),
    }

    create_response = client.post("/api/v1/products", json=product_data, headers=admin_headers)
    assert create_response.status_code == 201

    # Test search by name
    response = client.get("/api/v1/products?search=digital", headers=regular_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    # Should find the product we just created
    found_product = next((p for p in data["items"] if p["sku"] == "SEARCH-TEST-001"), None)
    assert found_product is not None

    # Test search by description content
    response = client.get("/api/v1/products?search=industrial", headers=regular_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

    # Test search with no results
    response = client.get("/api/v1/products?search=nonexistentterm", headers=regular_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_product_combined_filters(client: TestClient, regular_user_headers: dict[str, str]):
    """Test combining multiple filters."""
    response = client.get(
        "/api/v1/products?is_active=true&min_price=20&max_price=50&sort_by=price", headers=regular_user_headers
    )

    assert response.status_code == 200
    data = response.json()

    # All products should match the filters
    for product in data["items"]:
        assert product["is_active"] is True
        assert 20 <= product["price"] <= 50


def test_products_endpoints_have_prefix(client: TestClient, admin_headers: dict[str, str]):
    """Test all product endpoints are under /api/v1/products prefix."""
    # Should work
    response = client.get("/api/v1/products", headers=admin_headers)
    assert response.status_code == 200

    # Should not work (wrong prefix)
    response = client.get("/products", headers=admin_headers)
    assert response.status_code == 404
