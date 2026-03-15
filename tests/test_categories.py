"""Tests for category endpoints."""

import uuid

from fastapi.testclient import TestClient

from src.models.category import Category
from src.models.product import Product
from src.routers.categories import generate_slug


def test_list_categories_success(client: TestClient, regular_user_headers: dict[str, str]):
    """Test listing categories with pagination."""
    response = client.get("/api/v1/categories", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    # Check pagination structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

    # Should have seeded categories
    assert data["total"] >= 2  # At least Electronics and Sensors
    assert len(data["items"]) >= 2

    # Check category structure
    if data["items"]:
        category = data["items"][0]
        assert "id" in category
        assert "name" in category
        assert "slug" in category
        assert "description" in category
        assert "parent_id" in category
        assert "created_at" in category
        assert "updated_at" in category


def test_list_categories_pagination(client: TestClient, regular_user_headers: dict[str, str]):
    """Test category listing pagination."""
    response = client.get("/api/v1/categories?page=1&per_page=1", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["per_page"] == 1
    assert len(data["items"]) <= 1


def test_list_categories_no_auth(client: TestClient):
    """Test listing categories fails without authentication."""
    response = client.get("/api/v1/categories")

    assert response.status_code == 401


def test_create_category_success(client: TestClient, admin_headers: dict[str, str]):
    """Test successful category creation."""
    category_data = {"name": "Test Category", "description": "A test category", "parent_id": None}

    response = client.post("/api/v1/categories", json=category_data, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == category_data["name"]
    assert data["description"] == category_data["description"]
    assert data["parent_id"] is None
    assert data["slug"] == "test-category"  # Auto-generated slug
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_subcategory_success(client: TestClient, admin_headers: dict[str, str], test_category: Category):
    """Test creating a subcategory."""
    category_data = {
        "name": "Test Subcategory",
        "description": "A test subcategory",
        "parent_id": str(test_category.id),
    }

    response = client.post("/api/v1/categories", json=category_data, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == category_data["name"]
    assert data["parent_id"] == str(test_category.id)
    assert data["slug"] == "test-subcategory"


def test_create_category_invalid_parent(client: TestClient, admin_headers: dict[str, str]):
    """Test creating category with invalid parent ID."""
    category_data = {
        "name": "Test Category",
        "description": "A test category",
        "parent_id": str(uuid.uuid4()),  # Non-existent UUID
    }

    response = client.post("/api/v1/categories", json=category_data, headers=admin_headers)

    assert response.status_code == 400
    assert "Parent category not found" in response.json()["detail"]


def test_create_category_duplicate_name(client: TestClient, admin_headers: dict[str, str]):
    """Test creating category with duplicate name (which creates duplicate slug)."""
    # First create a category
    category_data = {"name": "Unique Category Name", "description": "First category"}
    response = client.post("/api/v1/categories", json=category_data, headers=admin_headers)
    assert response.status_code == 201

    # Try to create another with the same name (same slug)
    response = client.post("/api/v1/categories", json=category_data, headers=admin_headers)

    assert response.status_code == 409
    assert "slug already exists" in response.json()["detail"]


def test_create_category_non_admin(client: TestClient, regular_user_headers: dict[str, str]):
    """Test creating category fails for non-admin user."""
    category_data = {"name": "Test Category", "description": "A test category"}

    response = client.post("/api/v1/categories", json=category_data, headers=regular_user_headers)

    assert response.status_code == 403


def test_create_category_no_auth(client: TestClient):
    """Test creating category fails without authentication."""
    category_data = {"name": "Test Category", "description": "A test category"}

    response = client.post("/api/v1/categories", json=category_data)

    assert response.status_code == 401


def test_get_category_success(client: TestClient, regular_user_headers: dict[str, str], test_category: Category):
    """Test getting a category by ID."""
    response = client.get(f"/api/v1/categories/{test_category.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(test_category.id)
    assert data["name"] == test_category.name
    assert data["slug"] == test_category.slug
    assert "product_count" in data  # Should include product count


def test_get_category_not_found(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting non-existent category."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/categories/{fake_id}", headers=regular_user_headers)

    assert response.status_code == 404
    assert "Category not found" in response.json()["detail"]


def test_get_category_invalid_uuid(client: TestClient, regular_user_headers: dict[str, str]):
    """Test getting category with invalid UUID format."""
    response = client.get("/api/v1/categories/invalid-uuid", headers=regular_user_headers)

    assert response.status_code == 422  # UUID validation error


def test_update_category_success(client: TestClient, admin_headers: dict[str, str], test_category: Category):
    """Test successful category update."""
    update_data = {"name": "Updated Category Name", "description": "Updated description"}

    response = client.put(f"/api/v1/categories/{test_category.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["slug"] == "updated-category-name"  # Auto-updated slug
    assert data["id"] == str(test_category.id)


def test_update_category_partial(client: TestClient, admin_headers: dict[str, str], test_category: Category):
    """Test partial category update."""
    update_data = {"description": "Only updating description"}

    response = client.put(f"/api/v1/categories/{test_category.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["description"] == update_data["description"]
    assert data["name"] == test_category.name  # Should remain unchanged
    assert data["slug"] == test_category.slug  # Should remain unchanged


def test_update_category_self_parent(client: TestClient, admin_headers: dict[str, str], test_category: Category):
    """Test updating category to be its own parent (should fail)."""
    update_data = {"parent_id": str(test_category.id)}

    response = client.put(f"/api/v1/categories/{test_category.id}", json=update_data, headers=admin_headers)

    assert response.status_code == 400
    assert "cannot be its own parent" in response.json()["detail"]


def test_update_category_not_found(client: TestClient, admin_headers: dict[str, str]):
    """Test updating non-existent category."""
    fake_id = str(uuid.uuid4())
    update_data = {"name": "Updated Name"}

    response = client.put(f"/api/v1/categories/{fake_id}", json=update_data, headers=admin_headers)

    assert response.status_code == 404


def test_update_category_non_admin(client: TestClient, regular_user_headers: dict[str, str], test_category: Category):
    """Test updating category fails for non-admin user."""
    update_data = {"name": "Updated Name"}

    response = client.put(f"/api/v1/categories/{test_category.id}", json=update_data, headers=regular_user_headers)

    assert response.status_code == 403


def test_delete_category_success(client: TestClient, admin_headers: dict[str, str], db):
    """Test successful category deletion."""
    # Create a category without products
    category = Category(name="Category to Delete", slug="category-to-delete", description="Will be deleted")
    db.add(category)
    db.commit()
    db.refresh(category)

    response = client.delete(f"/api/v1/categories/{category.id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["detail"] == "Category deleted successfully"


def test_delete_category_with_products(
    client: TestClient, admin_headers: dict[str, str], test_category: Category, test_product: Product
):
    """Test deleting category with products fails."""
    # The test_category should have products from seeded data
    response = client.delete(f"/api/v1/categories/{test_category.id}", headers=admin_headers)

    assert response.status_code == 400
    assert "Cannot delete category with products" in response.json()["detail"]


def test_delete_category_not_found(client: TestClient, admin_headers: dict[str, str]):
    """Test deleting non-existent category."""
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/categories/{fake_id}", headers=admin_headers)

    assert response.status_code == 404


def test_delete_category_non_admin(client: TestClient, regular_user_headers: dict[str, str], test_category: Category):
    """Test deleting category fails for non-admin user."""
    response = client.delete(f"/api/v1/categories/{test_category.id}", headers=regular_user_headers)

    assert response.status_code == 403


def test_slug_generation():
    """Test slug generation function."""

    assert generate_slug("Simple Name") == "simple-name"
    assert generate_slug("Complex-Name_With@Special!Chars") == "complex-name-with-special-chars"
    assert generate_slug("  Leading and Trailing Spaces  ") == "leading-and-trailing-spaces"
    assert generate_slug("Multiple---Consecutive_Separators") == "multiple-consecutive-separators"
    assert generate_slug("Numbers123AndLetters") == "numbers123andletters"


def test_category_response_includes_product_count(
    client: TestClient, regular_user_headers: dict[str, str], test_category: Category
):
    """Test that category detail response includes product count."""
    response = client.get(f"/api/v1/categories/{test_category.id}", headers=regular_user_headers)

    assert response.status_code == 200
    data = response.json()

    assert "product_count" in data
    assert isinstance(data["product_count"], int)
    assert data["product_count"] >= 0  # Should be non-negative


def test_categories_endpoints_have_prefix(client: TestClient, admin_headers: dict[str, str]):
    """Test all category endpoints are under /api/v1/categories prefix."""
    # Should work
    response = client.get("/api/v1/categories", headers=admin_headers)
    assert response.status_code == 200

    # Should not work (wrong prefix)
    response = client.get("/categories", headers=admin_headers)
    assert response.status_code == 404
