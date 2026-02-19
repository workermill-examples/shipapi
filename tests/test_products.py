"""Tests for src/api/products.py — CRUD endpoints with full-text search, filters, and audit logging."""

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

from src.api.products import router as products_router
from src.database import get_db
from src.models import Category, Product, StockLevel, User, Warehouse
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


def _make_category_mock(
    *,
    name: str = "Electronics",
    description: str | None = "Electronic devices",
    parent_id: uuid.UUID | None = None,
) -> MagicMock:
    """Return a MagicMock shaped like a Category ORM instance."""
    cat = MagicMock(spec=Category)
    cat.id = uuid.uuid4()
    cat.name = name
    cat.description = description
    cat.parent_id = parent_id
    cat.created_at = datetime.now(UTC)
    cat.updated_at = datetime.now(UTC)
    return cat


def _make_warehouse_mock(
    *,
    name: str = "Main Warehouse",
    location: str = "Building A",
) -> MagicMock:
    """Return a MagicMock shaped like a Warehouse ORM instance."""
    wh = MagicMock(spec=Warehouse)
    wh.id = uuid.uuid4()
    wh.name = name
    wh.location = location
    return wh


def _make_stock_level_mock(
    *,
    warehouse: MagicMock | None = None,
    quantity: int = 50,
    min_threshold: int = 10,
) -> MagicMock:
    """Return a MagicMock shaped like a StockLevel ORM instance."""
    sl = MagicMock(spec=StockLevel)
    sl.warehouse_id = uuid.uuid4()
    sl.product_id = uuid.uuid4()
    sl.quantity = quantity
    sl.min_threshold = min_threshold
    sl.warehouse = warehouse if warehouse is not None else _make_warehouse_mock()
    return sl


def _make_product(
    *,
    name: str = "Widget",
    sku: str = "WID-001",
    description: str | None = "A test widget",
    price: Decimal = Decimal("9.99"),
    weight_kg: Decimal | None = Decimal("0.500"),
    is_active: bool = True,
    category: MagicMock | None = None,
) -> MagicMock:
    """Return a MagicMock shaped like a Product ORM instance with all fields set."""
    product = MagicMock(spec=Product)
    product.id = uuid.uuid4()
    product.name = name
    product.sku = sku
    product.description = description
    product.price = price
    product.weight_kg = weight_kg
    product.category_id = uuid.uuid4()
    product.is_active = is_active
    product.created_at = datetime.now(UTC)
    product.updated_at = datetime.now(UTC)
    product.category = category if category is not None else _make_category_mock()
    return product


def _make_app(db_mock: Any) -> FastAPI:
    """Build a minimal FastAPI app with the products router and overridden DB."""
    app = FastAPI()
    app.include_router(products_router)

    async def override_get_db() -> AsyncGenerator[Any]:
        yield db_mock

    app.dependency_overrides[get_db] = override_get_db
    return app


def _token(user: MagicMock) -> str:
    """Return a valid JWT access token for the given user."""
    return create_access_token(str(user.id), user.email, user.role)


def _make_paginated_db_mock(items: list[Any], total: int | None = None) -> AsyncMock:
    """Build a db mock that supports paginate()'s two execute() calls.

    The paginate utility calls db.execute() twice:
    1. A COUNT query → result.scalar_one() returns the total row count.
    2. A data query  → result.scalars().all() returns the page of items.
    """
    actual_total = total if total is not None else len(items)

    count_result = MagicMock()
    count_result.scalar_one.return_value = actual_total

    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = items

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[count_result, data_result])
    return db_mock


# ---------------------------------------------------------------------------
# GET /products — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_products_returns_paginated_envelope() -> None:
    """GET /products returns all products in a paginated data+pagination envelope."""
    p1 = _make_product(name="Alpha")
    p2 = _make_product(name="Beta")
    db_mock = _make_paginated_db_mock([p1, p2])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products")

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "pagination" in body
    assert len(body["data"]) == 2


@pytest.mark.asyncio
async def test_list_products_empty_returns_empty_list() -> None:
    """GET /products returns empty data list when no products exist."""
    db_mock = _make_paginated_db_mock([])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_list_products_no_auth_required() -> None:
    """GET /products is a public endpoint — no Authorization header needed."""
    db_mock = _make_paginated_db_mock([])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products")  # no auth header

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_products_pagination_params() -> None:
    """GET /products respects page and per_page query parameters."""
    db_mock = _make_paginated_db_mock([], total=50)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?page=2&per_page=10")

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["page"] == 2
    assert body["pagination"]["per_page"] == 10
    assert body["pagination"]["total"] == 50


@pytest.mark.asyncio
async def test_list_products_per_page_clamped_to_100() -> None:
    """GET /products silently clamps per_page to a maximum of 100."""
    db_mock = _make_paginated_db_mock([], total=0)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?per_page=200")

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["per_page"] == 100


@pytest.mark.asyncio
async def test_list_products_filter_by_is_active() -> None:
    """GET /products with is_active=true returns 200 and applies the filter."""
    active_product = _make_product(name="Active", is_active=True)
    db_mock = _make_paginated_db_mock([active_product])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?is_active=true")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.asyncio
async def test_list_products_filter_by_category_id() -> None:
    """GET /products with category_id returns 200 and applies the filter."""
    category_id = uuid.uuid4()
    cat_mock = _make_category_mock()
    cat_mock.id = category_id
    product = _make_product(name="Filtered", category=cat_mock)
    product.category_id = category_id

    db_mock = _make_paginated_db_mock([product])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/products?category_id={category_id}")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_products_filter_by_price_range() -> None:
    """GET /products with min_price and max_price filters by price range."""
    product = _make_product(name="Mid-range", price=Decimal("25.00"))
    db_mock = _make_paginated_db_mock([product])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?min_price=10.00&max_price=50.00")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.asyncio
async def test_list_products_search_parameter_accepted() -> None:
    """GET /products with search parameter triggers full-text search and returns 200."""
    product = _make_product(name="Widget Pro")
    db_mock = _make_paginated_db_mock([product])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?search=widget")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_products_sort_params_accepted() -> None:
    """GET /products accepts sort_by and sort_order query parameters."""
    db_mock = _make_paginated_db_mock([])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?sort_by=price&sort_order=asc")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_products_all_sort_fields_accepted() -> None:
    """GET /products accepts all valid sort_by values: name, price, created_at, sku."""
    for sort_field in ("name", "price", "created_at", "sku"):
        db_mock = _make_paginated_db_mock([])
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/products?sort_by={sort_field}")
        assert response.status_code == 200, f"Expected 200 for sort_by={sort_field}"


@pytest.mark.asyncio
async def test_list_products_invalid_sort_by_returns_422() -> None:
    """GET /products with an invalid sort_by value returns 422."""
    db_mock = _make_paginated_db_mock([])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products?sort_by=invalid_field")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_products_combined_filters_accepted() -> None:
    """GET /products supports combining multiple filters simultaneously."""
    category_id = uuid.uuid4()
    db_mock = _make_paginated_db_mock([])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/products?category_id={category_id}&min_price=5.00&max_price=100.00&is_active=true"
        )

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /products — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_product_authenticated_success() -> None:
    """Authenticated user can create a product and receives 201 with the created resource."""
    user = _make_user(role="user")
    token = _token(user)
    category_id = uuid.uuid4()
    cat_mock = _make_category_mock()
    cat_mock.id = category_id

    product_mock = _make_product(name="New Product", sku="NEW-001", category=cat_mock)
    product_mock.category_id = category_id

    async def fake_refresh(obj: Any) -> None:
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)
    db_mock.execute = AsyncMock(return_value=reload_result)

    with patch("src.api.products.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/products",
                json={
                    "name": "New Product",
                    "sku": "NEW-001",
                    "price": "9.99",
                    "category_id": str(category_id),
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Product"
    assert data["sku"] == "NEW-001"
    assert "id" in data
    assert "created_at" in data
    assert "category" in data


@pytest.mark.asyncio
async def test_create_product_admin_also_succeeds() -> None:
    """Admin (elevated role) can also create products — create is not admin-only."""
    admin = _make_user(role="admin")
    token = _token(admin)
    category_id = uuid.uuid4()
    cat_mock = _make_category_mock()
    cat_mock.id = category_id
    product_mock = _make_product(name="Admin Widget", sku="ADM-001", category=cat_mock)
    product_mock.category_id = category_id

    async def fake_refresh(obj: Any) -> None:
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)
    db_mock.execute = AsyncMock(return_value=reload_result)

    with patch("src.api.products.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/products",
                json={
                    "name": "Admin Widget",
                    "sku": "ADM-001",
                    "price": "5.00",
                    "category_id": str(category_id),
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_product_unauthenticated_returns_401() -> None:
    """Unauthenticated request to POST /products returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={
                "name": "Widget",
                "sku": "W-001",
                "price": "1.00",
                "category_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_product_missing_name_returns_422() -> None:
    """POST /products without required name field returns 422."""
    user = _make_user()
    token = _token(user)
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={"sku": "W-001", "price": "1.00", "category_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_missing_sku_returns_422() -> None:
    """POST /products without required sku field returns 422."""
    user = _make_user()
    token = _token(user)
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={"name": "Widget", "price": "1.00", "category_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_missing_price_returns_422() -> None:
    """POST /products without required price field returns 422."""
    user = _make_user()
    token = _token(user)
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={"name": "Widget", "sku": "W-001", "category_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_missing_category_id_returns_422() -> None:
    """POST /products without required category_id field returns 422."""
    user = _make_user()
    token = _token(user)
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={"name": "Widget", "sku": "W-001", "price": "1.00"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_negative_price_returns_422() -> None:
    """POST /products with a negative price returns 422."""
    user = _make_user()
    token = _token(user)
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={
                "name": "Widget",
                "sku": "W-001",
                "price": "-5.00",
                "category_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_name_too_long_returns_422() -> None:
    """POST /products with name exceeding 200 characters returns 422."""
    user = _make_user()
    token = _token(user)
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={
                "name": "X" * 201,
                "sku": "W-001",
                "price": "1.00",
                "category_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_sku_too_long_returns_422() -> None:
    """POST /products with SKU exceeding 50 characters returns 422."""
    user = _make_user()
    token = _token(user)
    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/products",
            json={
                "name": "Widget",
                "sku": "S" * 51,
                "price": "1.00",
                "category_id": str(uuid.uuid4()),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_product_invalid_category_id_returns_400() -> None:
    """POST /products with a non-existent category_id returns 400."""
    user = _make_user()
    token = _token(user)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock(side_effect=IntegrityError("FK violation", {}, Exception()))
    db_mock.rollback = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/products",
                json={
                    "name": "Widget",
                    "sku": "W-001",
                    "price": "1.00",
                    "category_id": str(uuid.uuid4()),
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 400
    assert "category_id" in response.json()["detail"]
    db_mock.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_product_writes_audit_log() -> None:
    """POST /products calls record_audit with action=create and resource_type=product."""
    user = _make_user()
    token = _token(user)
    category_id = uuid.uuid4()
    cat_mock = _make_category_mock()
    cat_mock.id = category_id
    product_mock = _make_product(category=cat_mock)
    product_mock.category_id = category_id

    async def fake_refresh(obj: Any) -> None:
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)
    db_mock.execute = AsyncMock(return_value=reload_result)

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/products",
                json={
                    "name": "Widget",
                    "sku": "W-001",
                    "price": "1.00",
                    "category_id": str(category_id),
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["action"] == "create"
    assert kwargs["resource_type"] == "product"
    assert kwargs["user_id"] == user.id


@pytest.mark.asyncio
async def test_create_product_audit_changes_include_all_fields() -> None:
    """Audit log for create includes the full field snapshot."""
    user = _make_user()
    token = _token(user)
    category_id = uuid.uuid4()
    cat_mock = _make_category_mock()
    cat_mock.id = category_id
    product_mock = _make_product(category=cat_mock)
    product_mock.category_id = category_id

    async def fake_refresh(obj: Any) -> None:
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.add = MagicMock()
    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=fake_refresh)
    db_mock.execute = AsyncMock(return_value=reload_result)

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post(
                "/products",
                json={
                    "name": "Audited Widget",
                    "sku": "AUD-001",
                    "price": "19.99",
                    "category_id": str(category_id),
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    changes = mock_audit.call_args.kwargs["changes"]
    assert changes["name"] == "Audited Widget"
    assert changes["sku"] == "AUD-001"
    # price is serialized to string in create audit
    assert changes["price"] == "19.99"
    assert changes["category_id"] == str(category_id)


# ---------------------------------------------------------------------------
# GET /products/{id} — detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_product_returns_detail_with_stock_levels() -> None:
    """GET /products/{id} returns product detail including stock levels."""
    warehouse_mock = _make_warehouse_mock(name="Main", location="Building A")
    stock_mock = _make_stock_level_mock(warehouse=warehouse_mock, quantity=100, min_threshold=10)
    product_mock = _make_product(name="Widget")

    product_result = MagicMock()
    product_result.scalar_one_or_none.return_value = product_mock

    sl_result = MagicMock()
    sl_result.scalars.return_value.all.return_value = [stock_mock]

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[product_result, sl_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/products/{product_mock.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Widget"
    assert len(data["stock_levels"]) == 1
    assert data["stock_levels"][0]["quantity"] == 100
    assert data["stock_levels"][0]["min_threshold"] == 10
    assert data["stock_levels"][0]["warehouse"]["name"] == "Main"
    assert data["stock_levels"][0]["warehouse"]["location"] == "Building A"


@pytest.mark.asyncio
async def test_get_product_returns_empty_stock_levels_when_none() -> None:
    """GET /products/{id} returns empty stock_levels list when no stock exists."""
    product_mock = _make_product(name="Unstocked Widget")

    product_result = MagicMock()
    product_result.scalar_one_or_none.return_value = product_mock

    sl_result = MagicMock()
    sl_result.scalars.return_value.all.return_value = []

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[product_result, sl_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/products/{product_mock.id}")

    assert response.status_code == 200
    assert response.json()["stock_levels"] == []


@pytest.mark.asyncio
async def test_get_product_includes_category_info() -> None:
    """GET /products/{id} includes nested category information."""
    cat_mock = _make_category_mock(name="Electronics", description="Gadgets")
    product_mock = _make_product(name="Laptop", category=cat_mock)

    product_result = MagicMock()
    product_result.scalar_one_or_none.return_value = product_mock

    sl_result = MagicMock()
    sl_result.scalars.return_value.all.return_value = []

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[product_result, sl_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/products/{product_mock.id}")

    assert response.status_code == 200
    data = response.json()
    assert "category" in data
    assert data["category"]["name"] == "Electronics"


@pytest.mark.asyncio
async def test_get_product_multiple_stock_levels() -> None:
    """GET /products/{id} returns all stock levels across multiple warehouses."""
    wh1 = _make_warehouse_mock(name="Warehouse A", location="NYC")
    wh2 = _make_warehouse_mock(name="Warehouse B", location="LA")
    sl1 = _make_stock_level_mock(warehouse=wh1, quantity=20)
    sl2 = _make_stock_level_mock(warehouse=wh2, quantity=30)
    product_mock = _make_product(name="Distributed Widget")

    product_result = MagicMock()
    product_result.scalar_one_or_none.return_value = product_mock

    sl_result = MagicMock()
    sl_result.scalars.return_value.all.return_value = [sl1, sl2]

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[product_result, sl_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/products/{product_mock.id}")

    assert response.status_code == 200
    assert len(response.json()["stock_levels"]) == 2


@pytest.mark.asyncio
async def test_get_product_not_found_returns_404() -> None:
    """GET /products/{id} with an unknown id returns 404."""
    product_result = MagicMock()
    product_result.scalar_one_or_none.return_value = None

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=product_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/products/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.asyncio
async def test_get_product_invalid_uuid_returns_422() -> None:
    """GET /products/{id} with a non-UUID path parameter returns 422."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/products/not-a-valid-uuid")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_product_no_auth_required() -> None:
    """GET /products/{id} is a public endpoint — no Authorization header needed."""
    product_mock = _make_product(name="Public Widget")

    product_result = MagicMock()
    product_result.scalar_one_or_none.return_value = product_mock

    sl_result = MagicMock()
    sl_result.scalars.return_value.all.return_value = []

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[product_result, sl_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/products/{product_mock.id}")  # no auth header

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# PUT /products/{id} — update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_product_authenticated_success() -> None:
    """Authenticated user can update a product; response is 200 with updated data."""
    user = _make_user(role="user")
    token = _token(user)
    cat_mock = _make_category_mock()
    product_mock = _make_product(name="Old Name", sku="OLD-001", category=cat_mock)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(side_effect=[fetch_result, reload_result])
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/products/{product_mock.id}",
                json={"name": "New Name"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_product_records_diff_in_audit() -> None:
    """Audit log records old and new values for each changed field."""
    user = _make_user()
    token = _token(user)
    cat_mock = _make_category_mock()
    product_mock = _make_product(name="Before", price=Decimal("10.00"), category=cat_mock)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(side_effect=[fetch_result, reload_result])
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                f"/products/{product_mock.id}",
                json={"name": "After"},
                headers={"Authorization": f"Bearer {token}"},
            )

    changes = mock_audit.call_args.kwargs["changes"]
    assert "name" in changes
    assert changes["name"]["old"] == "Before"
    assert changes["name"]["new"] == "After"


@pytest.mark.asyncio
async def test_update_product_no_changes_skips_audit_and_commit() -> None:
    """Sending a value equal to the current value skips both audit and DB commit."""
    user = _make_user()
    token = _token(user)
    cat_mock = _make_category_mock()
    product_mock = _make_product(name="Same Name", category=cat_mock)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(side_effect=[fetch_result, reload_result])
    db_mock.commit = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/products/{product_mock.id}",
                json={"name": "Same Name"},  # same value as current
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    mock_audit.assert_not_awaited()
    db_mock.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_product_empty_body_skips_audit() -> None:
    """Empty update body skips audit and commit, returning the unchanged product."""
    user = _make_user()
    token = _token(user)
    cat_mock = _make_category_mock()
    product_mock = _make_product(name="Unchanged", category=cat_mock)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(side_effect=[fetch_result, reload_result])
    db_mock.commit = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/products/{product_mock.id}",
                json={},  # nothing to update
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    mock_audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_product_writes_audit_log() -> None:
    """Update endpoint calls record_audit with action=update and correct resource_type."""
    user = _make_user()
    token = _token(user)
    cat_mock = _make_category_mock()
    product_mock = _make_product(name="Before", category=cat_mock)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(side_effect=[fetch_result, reload_result])
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                f"/products/{product_mock.id}",
                json={"name": "After"},
                headers={"Authorization": f"Bearer {token}"},
            )

    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["action"] == "update"
    assert kwargs["resource_type"] == "product"
    assert kwargs["user_id"] == user.id


@pytest.mark.asyncio
async def test_update_product_price_serialized_as_string_in_audit() -> None:
    """Audit log serializes Decimal price values to strings for JSON safety."""
    user = _make_user()
    token = _token(user)
    cat_mock = _make_category_mock()
    product_mock = _make_product(name="Widget", price=Decimal("10.00"), category=cat_mock)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(side_effect=[fetch_result, reload_result])
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                f"/products/{product_mock.id}",
                json={"price": "20.00"},
                headers={"Authorization": f"Bearer {token}"},
            )

    changes = mock_audit.call_args.kwargs["changes"]
    assert "price" in changes
    # Both old and new Decimal values must be serialized to strings
    assert isinstance(changes["price"]["old"], str)
    assert isinstance(changes["price"]["new"], str)


@pytest.mark.asyncio
async def test_update_product_category_id_serialized_as_string_in_audit() -> None:
    """Audit log serializes UUID category_id values to strings for JSON safety."""
    user = _make_user()
    token = _token(user)
    old_category_id = uuid.uuid4()
    cat_mock = _make_category_mock()
    cat_mock.id = old_category_id
    product_mock = _make_product(name="Widget", category=cat_mock)
    product_mock.category_id = old_category_id

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    reload_result = MagicMock()
    reload_result.scalar_one.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(side_effect=[fetch_result, reload_result])
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    new_category_id = uuid.uuid4()
    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.put(
                f"/products/{product_mock.id}",
                json={"category_id": str(new_category_id)},
                headers={"Authorization": f"Bearer {token}"},
            )

    changes = mock_audit.call_args.kwargs["changes"]
    assert "category_id" in changes
    # UUID values must be serialized to strings
    assert isinstance(changes["category_id"]["old"], str)
    assert isinstance(changes["category_id"]["new"], str)


@pytest.mark.asyncio
async def test_update_product_unauthenticated_returns_401() -> None:
    """Unauthenticated request to PUT /products/{id} returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(f"/products/{uuid.uuid4()}", json={"name": "X"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_product_not_found_returns_404() -> None:
    """PUT /products/{id} for a missing product returns 404."""
    user = _make_user()
    token = _token(user)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = None

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(return_value=fetch_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/products/{uuid.uuid4()}",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.asyncio
async def test_update_product_invalid_category_id_returns_400() -> None:
    """PUT /products/{id} with a non-existent category_id returns 400."""
    user = _make_user()
    token = _token(user)
    cat_mock = _make_category_mock()
    product_mock = _make_product(name="Widget", category=cat_mock)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=user)
    db_mock.execute = AsyncMock(return_value=fetch_result)
    db_mock.commit = AsyncMock(side_effect=IntegrityError("FK violation", {}, Exception()))
    db_mock.rollback = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/products/{product_mock.id}",
                json={"category_id": str(uuid.uuid4())},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 400
    db_mock.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# DELETE /products/{id} — soft-delete (admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_product_admin_success() -> None:
    """Admin can soft-delete a product; response is 204 No Content."""
    admin = _make_user(role="admin")
    token = _token(admin)
    product_mock = _make_product(name="To Be Deleted", is_active=True)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=fetch_result)
    db_mock.commit = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/products/{product_mock.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 204
    assert response.content == b""  # 204 has no body
    mock_audit.assert_awaited_once()
    kwargs = mock_audit.call_args.kwargs
    assert kwargs["action"] == "delete"
    assert kwargs["resource_type"] == "product"


@pytest.mark.asyncio
async def test_delete_product_sets_is_active_false() -> None:
    """Soft-delete sets is_active=False on the product — does NOT delete the row."""
    admin = _make_user(role="admin")
    token = _token(admin)
    product_mock = _make_product(name="Active Product", is_active=True)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=fetch_result)
    db_mock.commit = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock):
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.delete(
                f"/products/{product_mock.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    # is_active was set to False (soft delete)
    assert product_mock.is_active is False
    # db.delete() must NOT have been called — soft delete only
    db_mock.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_product_writes_audit_log() -> None:
    """Delete endpoint calls record_audit with correct user_id, resource_id, and action."""
    admin = _make_user(role="admin")
    token = _token(admin)
    product_mock = _make_product(name="Audited Product")

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=fetch_result)
    db_mock.commit = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.delete(
                f"/products/{product_mock.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    kwargs = mock_audit.call_args.kwargs
    assert kwargs["user_id"] == admin.id
    assert kwargs["resource_id"] == product_mock.id
    assert kwargs["action"] == "delete"
    assert kwargs["resource_type"] == "product"


@pytest.mark.asyncio
async def test_delete_product_audit_includes_name_and_sku() -> None:
    """Delete audit log includes the product's name and sku in changes."""
    admin = _make_user(role="admin")
    token = _token(admin)
    product_mock = _make_product(name="Delete Me", sku="DEL-001")

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = product_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=fetch_result)
    db_mock.commit = AsyncMock()

    with patch("src.api.products.record_audit", new_callable=AsyncMock) as mock_audit:
        app = _make_app(db_mock)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.delete(
                f"/products/{product_mock.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    changes = mock_audit.call_args.kwargs["changes"]
    assert changes["name"] == "Delete Me"
    assert changes["sku"] == "DEL-001"


@pytest.mark.asyncio
async def test_delete_product_unauthenticated_returns_401() -> None:
    """Unauthenticated request to DELETE /products/{id} returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(f"/products/{uuid.uuid4()}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_product_non_admin_returns_403() -> None:
    """Non-admin user receives 403 when attempting to delete a product."""
    regular_user = _make_user(role="user")
    token = _token(regular_user)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=regular_user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/products/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_product_not_found_returns_404() -> None:
    """DELETE /products/{id} for a missing product returns 404."""
    admin = _make_user(role="admin")
    token = _token(admin)

    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = None

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(return_value=fetch_result)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/products/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
