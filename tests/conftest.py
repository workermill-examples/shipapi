"""Shared pytest fixtures for the ShipAPI integration test suite.

The module-level environment setup runs at collection time — before any
``src.*`` module is imported.  This ensures pydantic-settings picks up the
test database URL rather than the default dev URL from ``.env``.

Fixture scopes
--------------
* ``test_db``       — session: create ``shipapi_test``, run migrations, drop.
* ``async_client``  — function: httpx client wrapping the full FastAPI app.
* ``auth_headers``  — function: register + login a regular user.
* ``admin_headers`` — function: register a user and elevate to admin.
* ``seeded_db``     — function: truncate all tables, seed representative data.
* ``reset_rate_limiter`` — function, autouse: prevent cross-test counter bleed.
"""

import asyncio
import os
import subprocess
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Test database configuration
# ---------------------------------------------------------------------------

_TEST_DB_NAME = "shipapi_test"
_DB_HOST = os.getenv("DB_HOST", "localhost")
# Default port matches the workermill platform's shared PostgreSQL instance.
# Override with DB_PORT=5432 when running the project's own docker-compose.
_DB_PORT = os.getenv("DB_PORT", "5433")
_DB_USER = os.getenv("DB_USER", "workermill")
_DB_PASSWORD = os.getenv("DB_PASSWORD", "localdev")
# Connect to this existing DB to run CREATE / DROP DATABASE statements.
_DB_ADMIN_DB = os.getenv("DB_ADMIN_DB", "workermill")

_TEST_DB_URL = (
    f"postgresql+asyncpg://{_DB_USER}:{_DB_PASSWORD}@{_DB_HOST}:{_DB_PORT}/{_TEST_DB_NAME}"
)
# Plain asyncpg URL (no "+asyncpg" driver qualifier) used for admin connections.
_TEST_ADMIN_CONN_URL = (
    f"postgresql://{_DB_USER}:{_DB_PASSWORD}@{_DB_HOST}:{_DB_PORT}/{_DB_ADMIN_DB}"
)

# ---------------------------------------------------------------------------
# Environment bootstrap — must run before any ``src.*`` import
# ---------------------------------------------------------------------------

# Override (not setdefault) so tests never accidentally hit the dev DB.
os.environ["DATABASE_URL"] = _TEST_DB_URL
# DATABASE_URL_DIRECT is only needed by the Alembic subprocess.  It is passed
# explicitly in the test_db fixture env dict rather than set here so that
# test_config.py::test_settings_defaults can still assert the default is None.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")

# ---------------------------------------------------------------------------
# Rate-limiter reset — prevents cross-test pollution of in-memory counters
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Reset the in-memory rate-limit storage before every test.

    The module-level ``limiter`` singleton accumulates counters across tests
    in the same process.  Without this fixture, low-limit endpoints (e.g.
    register: 5/minute) exhaust their quota during the test run.
    """
    from src.middleware.rate_limit import limiter

    limiter._storage.reset()


# ---------------------------------------------------------------------------
# Session: create test database + run Alembic migrations
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_db() -> Generator[str]:
    """Create ``shipapi_test``, run Alembic migrations, yield the URL.

    Uses :func:`asyncio.run` for DB admin operations so this synchronous
    session-scoped fixture avoids event-loop conflicts with pytest-asyncio's
    per-function event loops.  The test database is dropped on teardown.
    """

    async def _create_db() -> None:
        conn = await asyncpg.connect(_TEST_ADMIN_CONN_URL)
        try:
            # Terminate lingering connections from a previous failed run.
            await conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = $1 AND pid <> pg_backend_pid()",
                _TEST_DB_NAME,
            )
            await conn.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
            await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
        finally:
            await conn.close()

    async def _drop_db() -> None:
        conn = await asyncpg.connect(_TEST_ADMIN_CONN_URL)
        try:
            await conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = $1 AND pid <> pg_backend_pid()",
                _TEST_DB_NAME,
            )
            await conn.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
        finally:
            await conn.close()

    asyncio.run(_create_db())

    # Run Alembic migrations.  DATABASE_URL_DIRECT is passed explicitly to the
    # subprocess rather than set in the process env so that existing tests in
    # test_config.py can still assert settings.database_url_direct is None.
    subprocess.run(
        ["alembic", "upgrade", "head"],
        check=True,
        capture_output=True,
        env={**os.environ, "DATABASE_URL_DIRECT": _TEST_DB_URL},
    )

    yield _TEST_DB_URL

    asyncio.run(_drop_db())


# ---------------------------------------------------------------------------
# Function: async HTTP client backed by the real FastAPI app
# ---------------------------------------------------------------------------


@pytest.fixture
async def async_client(test_db: str) -> AsyncGenerator[AsyncClient]:  # noqa: ARG001
    """httpx.AsyncClient that drives the full FastAPI app in-process.

    The ASGI lifespan (engine connection verification) fires on context entry
    and exit, so ``test_db`` must have already created and migrated the
    database — guaranteed by the fixture dependency.
    """
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


@pytest.fixture
async def auth_headers(async_client: AsyncClient) -> dict[str, str]:
    """Register and log in a regular user; return ``Authorization`` headers.

    Uses a random suffix on the email so sequential test functions never
    collide on the unique email constraint.
    """
    suffix = uuid.uuid4().hex[:8]
    email = f"user_{suffix}@test.com"
    password = "TestPassword123!"

    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Test User", "password": password},
    )
    assert reg.status_code == 201, f"Registration failed: {reg.text}"

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
async def admin_headers(async_client: AsyncClient) -> dict[str, str]:
    """Register a user, promote to admin in the DB, and return auth headers.

    There is no admin-creation API endpoint, so role elevation is done
    directly via :class:`~src.database.AsyncSessionLocal`.
    """
    from src.database import AsyncSessionLocal

    suffix = uuid.uuid4().hex[:8]
    email = f"admin_{suffix}@test.com"
    password = "AdminPassword123!"

    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Test Admin", "password": password},
    )
    assert reg.status_code == 201, f"Admin registration failed: {reg.text}"

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE users SET role = 'admin' WHERE email = :email"),
            {"email": email},
        )
        await session.commit()

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, f"Admin login failed: {login.text}"
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Seeded database — representative data for integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded_db(async_client: AsyncClient) -> AsyncGenerator[dict[str, Any]]:
    """Truncate all tables and populate with representative seed data.

    Returns a mapping with created resource IDs, credentials, and auth
    headers so that tests using this fixture do not need to request
    ``auth_headers`` or ``admin_headers`` separately (which would conflict
    with the users-table truncation).

    Warehouses and stock levels are inserted directly via SQLAlchemy because
    those routers are not yet mounted in the main API router.
    """
    import uuid as _uuid

    from src.database import AsyncSessionLocal
    from src.models import StockLevel, Warehouse

    # ------------------------------------------------------------------
    # Truncate in FK-safe order; CASCADE handles the rest.
    # ------------------------------------------------------------------
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "TRUNCATE audit_logs, stock_transfers, stock_levels, "
                "products, categories, warehouses, users RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

    # ------------------------------------------------------------------
    # Create admin and regular users
    # ------------------------------------------------------------------
    suffix = uuid.uuid4().hex[:8]
    admin_email = f"seed_admin_{suffix}@test.com"
    admin_password = "SeedAdmin123!"
    user_email = f"seed_user_{suffix}@test.com"
    user_password = "SeedUser123!"

    reg_admin = await async_client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "name": "Seed Admin", "password": admin_password},
    )
    assert reg_admin.status_code == 201, f"Admin registration failed: {reg_admin.text}"

    reg_user = await async_client.post(
        "/api/v1/auth/register",
        json={"email": user_email, "name": "Seed User", "password": user_password},
    )
    assert reg_user.status_code == 201, f"User registration failed: {reg_user.text}"

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE users SET role = 'admin' WHERE email = :email"),
            {"email": admin_email},
        )
        await session.commit()

    login_admin = await async_client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    admin_token: str = login_admin.json()["access_token"]
    admin_auth: dict[str, str] = {"Authorization": f"Bearer {admin_token}"}

    login_user = await async_client.post(
        "/api/v1/auth/login",
        json={"email": user_email, "password": user_password},
    )
    user_token: str = login_user.json()["access_token"]
    user_auth: dict[str, str] = {"Authorization": f"Bearer {user_token}"}

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------
    cat_resp = await async_client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "description": "Electronic devices and accessories"},
        headers=admin_auth,
    )
    assert cat_resp.status_code == 201, f"Category creation failed: {cat_resp.text}"
    category_id: str = cat_resp.json()["id"]

    sub_resp = await async_client.post(
        "/api/v1/categories",
        json={
            "name": "Peripherals",
            "description": "Computer peripherals",
            "parent_id": category_id,
        },
        headers=admin_auth,
    )
    assert sub_resp.status_code == 201, f"Sub-category creation failed: {sub_resp.text}"
    sub_category_id: str = sub_resp.json()["id"]

    # ------------------------------------------------------------------
    # Products (with searchable names / descriptions)
    # ------------------------------------------------------------------
    prod1 = await async_client.post(
        "/api/v1/products",
        json={
            "name": "4K Monitor",
            "sku": "MON-4K-001",
            "description": "Ultra HD 4K monitor for professional use",
            "price": "299.99",
            "category_id": category_id,
        },
        headers=admin_auth,
    )
    assert prod1.status_code == 201, f"Product 1 creation failed: {prod1.text}"
    product1_id: str = prod1.json()["id"]

    prod2 = await async_client.post(
        "/api/v1/products",
        json={
            "name": "Mechanical Keyboard",
            "sku": "KBD-MECH-001",
            "description": "Mechanical keyboard with RGB backlight",
            "price": "129.99",
            "category_id": sub_category_id,
        },
        headers=admin_auth,
    )
    assert prod2.status_code == 201, f"Product 2 creation failed: {prod2.text}"
    product2_id: str = prod2.json()["id"]

    prod3 = await async_client.post(
        "/api/v1/products",
        json={
            "name": "Wireless Mouse",
            "sku": "MSE-WRL-001",
            "description": "Ergonomic wireless mouse with long battery life",
            "price": "49.99",
            "category_id": sub_category_id,
        },
        headers=admin_auth,
    )
    assert prod3.status_code == 201, f"Product 3 creation failed: {prod3.text}"
    product3_id: str = prod3.json()["id"]

    # ------------------------------------------------------------------
    # Warehouses — inserted directly (warehouse router not yet mounted)
    # ------------------------------------------------------------------
    async with AsyncSessionLocal() as session:
        wh1 = Warehouse(name="Main Warehouse", location="Building A", capacity=1000)
        wh2 = Warehouse(name="Secondary Warehouse", location="Building B", capacity=500)
        session.add_all([wh1, wh2])
        await session.commit()
        await session.refresh(wh1)
        await session.refresh(wh2)
        warehouse_id: str = str(wh1.id)
        warehouse2_id: str = str(wh2.id)

    # ------------------------------------------------------------------
    # Stock levels — inserted directly.
    # product2 quantity (5) < min_threshold (20) — triggers stock alert tests.
    # ------------------------------------------------------------------
    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                StockLevel(
                    product_id=_uuid.UUID(product1_id),
                    warehouse_id=_uuid.UUID(warehouse_id),
                    quantity=50,
                    min_threshold=10,
                ),
                StockLevel(
                    product_id=_uuid.UUID(product2_id),
                    warehouse_id=_uuid.UUID(warehouse_id),
                    quantity=5,
                    min_threshold=20,
                ),
                StockLevel(
                    product_id=_uuid.UUID(product3_id),
                    warehouse_id=_uuid.UUID(warehouse2_id),
                    quantity=100,
                    min_threshold=15,
                ),
            ]
        )
        await session.commit()

    yield {
        "admin_email": admin_email,
        "admin_password": admin_password,
        "admin_auth": admin_auth,
        "admin_token": admin_token,
        "user_email": user_email,
        "user_password": user_password,
        "user_auth": user_auth,
        "user_token": user_token,
        "category_id": category_id,
        "sub_category_id": sub_category_id,
        "warehouse_id": warehouse_id,
        "warehouse2_id": warehouse2_id,
        "product1_id": product1_id,
        "product2_id": product2_id,
        "product3_id": product3_id,
    }
