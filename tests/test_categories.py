"""Tests for src/api/categories.py — CRUD endpoints with admin guards and cascade protection."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from src.api.categories import router as categories_router
from src.database import get_db
from src.models import Category, Product, User
from src.services.auth import create_access_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, role: str = "user", is_active: bool = True) -> MagicMock:
    """Return a MagicMock shaped like a User ORM instance."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.name = "Test User"
    user.role = role
    user.is_active = is_active
    return user


def _make_category(
    *,
    name: str = "Electronics",
    description: str | None = "Electronic devices",
    parent_id: uuid.UUID | None = None,
    products: list[Any] | None = None,
) -> MagicMock:
    """Return a MagicMock shaped like a Category ORM instance."""
    category = MagicMock(spec=Category)
    category.id = uuid.uuid4()
    category.name = name
    category.description = description
    category.parent_id = parent_id
    category.created_at = datetime.now(UTC)
    category.updated_at = datetime.now(UTC)
    category.products = products if products is not None else []
    return category


def _make_product(
    *,
    name: str = "Widget",
    sku: str = "WID-001",
    price: Decimal = Decimal("9.99"),
    is_active: bool = True,
) -> MagicMock:
    """Return a MagicMock shaped like a Product ORM instance."""
    product = MagicMock(spec=Product)
    product.id = uuid.uuid4()
    product.name = name
    product.sku = sku
    product.price = price
    product.is_active = is_active
    product.created_at = datetime.now(UTC)
    return product


def _make_app(db_mock: Any) -> FastAPI:
    """Build a minimal FastAPI app with the categories router and overridden DB."""
    app = FastAPI()
    app.include_router(categories_router)

    async def override_get_db() -> AsyncGenerator[Any]:
        yield db_mock

    app.dependency_overrides[get_db] = override_get_db
    return app


def _token(user: MagicMock) -> str:
    """Return a valid JWT access token for the given user."""
    return create_access_token(str(user.id), user.email, user.role)


# ---------------------------------------------------------------------------
# GET /categories — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_categories_returns_flat_list() -> None:
    """GET /categories returns all categories ordered by name."""
    cat1 = _make_category(name="Appliances")
    cat2 = _make_category(name="Electronics")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [cat1, cat2]

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/categories")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Appliances"
    assert data[1]["name"] == "Electronics"


@pytest.mark.asyncio
async def test_list_categories_empty_returns_empty_list() -> None:
    """GET /categories returns [] when no categories exist."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/categories")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_categories_includes_parent_id() -> None:
    """GET /categories exposes parent_id on subcategories."""
    parent_id = uuid.uuid4()
    parent = _make_category(name="Parent")
    child = _make_category(name="Child", parent_id=parent_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [child, parent]

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/categories")

    data = response.json()
    child_data = next(d for d in data if d["name"] == "Child")
    assert child_data["parent_id"] == str(parent_id)


@pytest.mark.asyncio
async def test_list_categories_no_auth_required() -> None:
    """GET /categories is a public endpoint — no Authorization header needed."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/categories")  # no auth header

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /categories — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_category_admin_success() -> None:
    """Admin can create a new category and receives 201 with the created resource."""
    admin = _make_user(role="admin")
    token = _token(admin)

    async def fake_refresh(obj: Any) -> None:
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)

    with patch("src.api.categories.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/categories",
                json={"name": "New Cat", "description": "A new category"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Cat"
    assert data["description"] == "A new category"
    assert data["parent_id"] is None
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_category_with_parent_id() -> None:
    """Admin can create a subcategory by providing a valid parent_id."""
    admin = _make_user(role="admin")
    token = _token(admin)
    parent_id = uuid.uuid4()

    async def fake_refresh(obj: Any) -> None:
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)

    with patch("src.api.categories.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/categories",
                json={"name": "Sub Cat", "parent_id": str(parent_id)},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["parent_id"] == str(parent_id)


@pytest.mark.asyncio
async def test_create_category_non_admin_returns_403() -> None:
    """Non-admin user receives 403 when attempting to create a category."""
    regular_user = _make_user(role="user")
    token = _token(regular_user)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=regular_user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/categories",
            json={"name": "New Cat"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_category_unauthenticated_returns_401() -> None:
    """Unauthenticated request to POST /categories returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/categories", json={"name": "New Cat"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_category_invalid_parent_returns_400() -> None:
    """Creating a category with a non-existent parent_id returns 400."""
    admin = _make_user(role="admin")
    token = _token(admin)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock(side_effect=IntegrityError("FK violation", {}, Exception()))
    db_mock.rollback = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/categories",
                json={"name": "Sub Cat", "parent_id": str(uuid.uuid4())},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 400
    assert "parent_id" in response.json()["detail"]
    db_mock.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_category_name_too_long_returns_422() -> None:
    """Category name exceeding 100 characters fails Pydantic validation with 422."""
    admin = _make_user(role="admin")
    token = _token(admin)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/categories",
            json={"name": "X" * 101},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_category_missing_name_returns_422() -> None:
    """Category body without required name field returns 422."""
    admin = _make_user(role="admin")
    token = _token(admin)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/categories",
            json={"description": "No name"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_category_writes_audit_log() -> None:
    """Create endpoint calls record_audit with action=create and resource_type=category."""
    admin = _make_user(role="admin")
    token = _token(admin)

    async def fake_refresh(obj: Any) -> None:
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)

    with patch("src.api.categories.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/categories",
                json={"name": "Audit Cat"},
                headers={"Authorization": f"Bearer {token}"},
            )

    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["action"] == "create"
    assert kwargs["resource_type"] == "category"
    assert kwargs["user_id"] == admin.id


# ---------------------------------------------------------------------------
# GET /categories/{id} — detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_category_returns_detail_with_products() -> None:
    """GET /categories/{id} returns category detail including its products."""
    product = _make_product(name="Widget", sku="WID-001")
    category = _make_category(name="Electronics", products=[product])

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/categories/{category.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Electronics"
    assert len(data["products"]) == 1
    assert data["products"][0]["name"] == "Widget"
    assert data["products"][0]["sku"] == "WID-001"


@pytest.mark.asyncio
async def test_get_category_returns_empty_products_list() -> None:
    """GET /categories/{id} returns empty products list when category has no products."""
    category = _make_category(name="Empty Category", products=[])

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/categories/{category.id}")

    assert response.status_code == 200
    assert response.json()["products"] == []


@pytest.mark.asyncio
async def test_get_category_not_found_returns_404() -> None:
    """GET /categories/{id} with an unknown id returns 404."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/categories/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


@pytest.mark.asyncio
async def test_get_category_invalid_uuid_returns_422() -> None:
    """GET /categories/{id} with a non-UUID path parameter returns 422."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/categories/not-a-valid-uuid")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_category_no_auth_required() -> None:
    """GET /categories/{id} is a public endpoint — no Authorization header needed."""
    category = _make_category(name="Public Cat")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/categories/{category.id}")  # no auth header

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# PUT /categories/{id} — update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_category_admin_success() -> None:
    """Admin can update a category's name; response is 200 with updated data."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Old Name", description="Old Desc")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/categories/{category.id}",
                json={"name": "New Name"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_category_records_diff_in_audit() -> None:
    """Audit log records old and new values of each changed field."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Original Name", description=None)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                f"/categories/{category.id}",
                json={"name": "Updated Name"},
                headers={"Authorization": f"Bearer {token}"},
            )

    changes = mock_audit.call_args.kwargs["changes"]
    assert "name" in changes
    assert changes["name"]["old"] == "Original Name"
    assert changes["name"]["new"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_category_no_changes_skips_audit_and_commit() -> None:
    """Sending a value equal to the current value skips both audit and DB commit."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Same Name")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)
    db_mock.commit = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/categories/{category.id}",
                json={"name": "Same Name"},  # same value as current
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    mock_audit.assert_not_awaited()
    db_mock.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_category_empty_body_skips_audit() -> None:
    """Empty update body skips audit and commit, returning the unchanged category."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Cat")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)
    db_mock.commit = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/categories/{category.id}",
                json={},  # nothing to update
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    mock_audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_category_writes_audit_log() -> None:
    """Update endpoint calls record_audit with action=update and the correct resource_type."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Before")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                f"/categories/{category.id}",
                json={"name": "After"},
                headers={"Authorization": f"Bearer {token}"},
            )

    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["action"] == "update"
    assert kwargs["resource_type"] == "category"
    assert kwargs["user_id"] == admin.id


@pytest.mark.asyncio
async def test_update_category_non_admin_returns_403() -> None:
    """Non-admin user receives 403 when attempting to update a category."""
    regular_user = _make_user(role="user")
    token = _token(regular_user)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=regular_user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/categories/{uuid.uuid4()}",
            json={"name": "Hacked"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_category_unauthenticated_returns_401() -> None:
    """Unauthenticated request to PUT /categories/{id} returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(f"/categories/{uuid.uuid4()}", json={"name": "X"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_category_not_found_returns_404() -> None:
    """PUT /categories/{id} for a missing category returns 404."""
    admin = _make_user(role="admin")
    token = _token(admin)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/categories/{uuid.uuid4()}",
            json={"name": "New"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


@pytest.mark.asyncio
async def test_update_category_invalid_parent_returns_400() -> None:
    """Setting parent_id to a non-existent category id returns 400."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Cat", parent_id=None)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)
    db_mock.commit = AsyncMock(side_effect=IntegrityError("FK violation", {}, Exception()))
    db_mock.rollback = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/categories/{category.id}",
                json={"parent_id": str(uuid.uuid4())},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 400
    assert "parent_id" in response.json()["detail"]
    db_mock.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# DELETE /categories/{id} — delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_category_admin_success() -> None:
    """Admin can delete a category with no products; response is 204 No Content."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Empty Cat")

    mock_cat_result = MagicMock()
    mock_cat_result.scalar_one_or_none.return_value = category
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0  # no products

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[mock_cat_result, mock_count_result])
    db_mock.delete = AsyncMock()
    db_mock.commit = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/categories/{category.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 204
    assert response.content == b""  # 204 has no body
    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["action"] == "delete"
    assert kwargs["resource_type"] == "category"
    db_mock.delete.assert_awaited_once_with(category)
    db_mock.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_category_writes_audit_log() -> None:
    """Delete endpoint calls record_audit with the correct user_id and resource."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Deleted Cat")

    mock_cat_result = MagicMock()
    mock_cat_result.scalar_one_or_none.return_value = category
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[mock_cat_result, mock_count_result])
    db_mock.delete = AsyncMock()
    db_mock.commit = AsyncMock()

    with patch("src.api.categories.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.delete(
                f"/categories/{category.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    kwargs = mock_audit.call_args.kwargs
    assert kwargs["user_id"] == admin.id
    assert kwargs["resource_id"] == category.id


@pytest.mark.asyncio
async def test_delete_category_with_products_returns_400() -> None:
    """Deleting a category that has active products returns 400 (cascade protection)."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Busy Cat")

    mock_cat_result = MagicMock()
    mock_cat_result.scalar_one_or_none.return_value = category
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 3  # 3 products

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[mock_cat_result, mock_count_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/categories/{category.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 400
    assert "products" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_category_inactive_products_also_blocked() -> None:
    """Cascade protection triggers even when all products are inactive (is_active=false)."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category = _make_category(name="Cat With Inactive Products")

    mock_cat_result = MagicMock()
    mock_cat_result.scalar_one_or_none.return_value = category
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1  # 1 inactive product still counts

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[mock_cat_result, mock_count_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/categories/{category.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_category_non_admin_returns_403() -> None:
    """Non-admin user receives 403 when attempting to delete a category."""
    regular_user = _make_user(role="user")
    token = _token(regular_user)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=regular_user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/categories/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_category_unauthenticated_returns_401() -> None:
    """Unauthenticated request to DELETE /categories/{id} returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/categories/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_category_not_found_returns_404() -> None:
    """DELETE /categories/{id} for a missing category returns 404."""
    admin = _make_user(role="admin")
    token = _token(admin)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=mock_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/categories/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"
