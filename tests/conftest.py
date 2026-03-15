"""
Test configuration and fixtures for ShipAPI.

Provides fixtures for:
- Test database creation/cleanup with real PostgreSQL
- Alembic migrations for test schema
- Seed data for consistent test scenarios
- TestClient with FastAPI app
- Auth headers for admin and regular users
"""

import os
import sys
import uuid
from collections.abc import Generator
from pathlib import Path

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Fix alembic import issue - the local ./alembic directory conflicts with alembic package
# We need to import the alembic package, not the local directory
# Save the current path and remove current directory from it
_saved_path = sys.path[:]
sys.path = [p for p in sys.path if p != "" and os.path.abspath(p) != os.getcwd()]

# Now we can safely import alembic package
from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402

# Restore original path
sys.path = _saved_path

from src.auth import create_access_token, hash_password  # noqa: E402
from src.database import get_db  # noqa: E402
from src.main import create_app  # noqa: E402
from src.models import AuditLog, Category, Product, StockLevel, StockTransfer, User, Warehouse  # noqa: E402

# Test database configuration
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shipapi:shipapi@localhost:5432/shipapi_test").replace(
    "shipapi_test", "shipapi_test"
)

# Extract connection details for database creation
DB_URL_PARTS = TEST_DATABASE_URL.split("/")
DB_NAME = DB_URL_PARTS[-1]  # shipapi_test
DB_URL_WITHOUT_NAME = "/".join(DB_URL_PARTS[:-1])  # postgresql://user:pass@host:port


def _get_postgres_connection_params():
    """Parse TEST_DATABASE_URL to get connection parameters."""
    # Example: postgresql://shipapi:shipapi@localhost:5432/shipapi_test
    url_parts = TEST_DATABASE_URL.replace("postgresql://", "").split("/")

    auth_host = url_parts[0]  # shipapi:shipapi@localhost:5432
    if "@" in auth_host:
        auth, host_port = auth_host.split("@")
        user, password = auth.split(":")
    else:
        user, password = "shipapi", "shipapi"
        host_port = auth_host

    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host, port = host_port, 5432

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": "postgres",  # Connect to postgres for DB operations
    }


@pytest.fixture(scope="session")
def test_db_setup():
    """
    Session-scoped fixture to create and destroy test database.

    Creates the test database, runs Alembic migrations, and drops
    the database after all tests complete.
    """
    # Get connection parameters
    conn_params = _get_postgres_connection_params()

    # Create the test database using psycopg2
    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cursor:
        # Terminate existing connections to the test database
        cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (DB_NAME,))

        # Drop database if it exists and recreate
        cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(DB_NAME)))
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))

    conn.close()

    # Run Alembic migrations on the test database
    test_engine = create_engine(TEST_DATABASE_URL)

    # Set up Alembic configuration
    alembic_cfg = Config(Path(__file__).parent.parent / "alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    # Run migrations
    command.upgrade(alembic_cfg, "head")

    yield test_engine

    # Cleanup
    test_engine.dispose()

    # Drop the test database using psycopg2
    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cursor:
        # Terminate existing connections to the test database
        cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (DB_NAME,))

        # Drop the test database
        cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(DB_NAME)))

    conn.close()


@pytest.fixture
def db(test_db_setup) -> Generator[Session]:
    """
    Function-scoped database session fixture.

    Each test gets a clean database session with seeded data.
    Changes are rolled back after each test.
    """
    test_session_local = sessionmaker(bind=test_db_setup)

    # Start a transaction that we can rollback
    connection = test_db_setup.connect()
    transaction = connection.begin()

    # Create session bound to this connection
    db_session = test_session_local(bind=connection)

    try:
        # Seed test data
        _seed_test_data(db_session)
        yield db_session
    finally:
        db_session.close()
        transaction.rollback()
        connection.close()


def _seed_test_data(db: Session) -> None:
    """Seed the test database with minimal but realistic test data."""

    # Create admin user for testing
    admin_user = User(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        email="admin@test.com",
        username="admin_test",
        hashed_password=hash_password("admin123"),
        is_active=True,
        is_admin=True,
    )

    # Create regular user for testing
    regular_user = User(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        email="user@test.com",
        username="user_test",
        hashed_password=hash_password("user123"),
        is_active=True,
        is_admin=False,
    )

    db.add(admin_user)
    db.add(regular_user)

    # Create test categories
    electronics = Category(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        name="Electronics",
        slug="electronics",
        description="Electronic devices and components",
    )

    sensors = Category(
        id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        name="Sensors",
        slug="sensors",
        description="Various sensor types",
        parent_id=electronics.id,
    )

    db.add(electronics)
    db.add(sensors)

    # Create test warehouses
    warehouse_east = Warehouse(
        id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        name="East Coast Warehouse",
        code="EAST01",
        address="123 East St, New York, NY",
        is_active=True,
    )

    warehouse_west = Warehouse(
        id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        name="West Coast Warehouse",
        code="WEST01",
        address="456 West Ave, Los Angeles, CA",
        is_active=True,
    )

    db.add(warehouse_east)
    db.add(warehouse_west)

    # Create test products
    test_product = Product(
        id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        name="Temperature Sensor",
        sku="TEMP-001",
        description="High precision digital temperature sensor",
        price=25.99,
        is_active=True,
        category_id=sensors.id,
    )

    inactive_product = Product(
        id=uuid.UUID("88888888-8888-8888-8888-888888888888"),
        name="Discontinued Sensor",
        sku="DISC-001",
        description="Old sensor model",
        price=15.99,
        is_active=False,
        category_id=sensors.id,
    )

    db.add(test_product)
    db.add(inactive_product)

    # Commit to get product IDs for stock levels
    db.commit()

    # Create test stock levels
    stock_east = StockLevel(
        product_id=test_product.id,
        warehouse_id=warehouse_east.id,
        quantity=100,
        low_stock_threshold=10,
    )

    stock_west = StockLevel(
        product_id=test_product.id,
        warehouse_id=warehouse_west.id,
        quantity=5,  # Below threshold for alert testing
        low_stock_threshold=10,
    )

    db.add(stock_east)
    db.add(stock_west)

    # Create test stock transfer
    transfer = StockTransfer(
        product_id=test_product.id,
        from_warehouse_id=warehouse_east.id,
        to_warehouse_id=warehouse_west.id,
        quantity=20,
        notes="Test transfer",
    )

    db.add(transfer)

    # Create test audit log entry
    audit = AuditLog(
        user_id=admin_user.id,
        action="create",
        resource_type="product",
        resource_id=str(test_product.id),
        details={"name": "Temperature Sensor", "sku": "TEMP-001"},
        ip_address="127.0.0.1",
    )

    db.add(audit)
    db.commit()


@pytest.fixture
def client(db) -> TestClient:
    """
    FastAPI TestClient with overridden database dependency.

    Uses the test database session instead of the production database.
    """
    app = create_app()

    # Override the get_db dependency to use our test database
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """
    Authorization headers for admin user.

    Returns headers dict with JWT token for admin user.
    """
    admin_user_id = "11111111-1111-1111-1111-111111111111"
    token = create_access_token(data={"sub": admin_user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regular_user_headers() -> dict[str, str]:
    """
    Authorization headers for regular user.

    Returns headers dict with JWT token for regular user.
    """
    regular_user_id = "22222222-2222-2222-2222-222222222222"
    token = create_access_token(data={"sub": regular_user_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_user(db) -> User:
    """Get the seeded admin user."""
    admin_user = db.query(User).filter(User.email == "admin@test.com").first()
    return admin_user


@pytest.fixture
def regular_user(db) -> User:
    """Get the seeded regular user."""
    regular_user = db.query(User).filter(User.email == "user@test.com").first()
    return regular_user


@pytest.fixture
def test_category(db) -> Category:
    """Get the seeded test category."""
    category = db.query(Category).filter(Category.slug == "sensors").first()
    return category


@pytest.fixture
def test_product(db) -> Product:
    """Get the seeded test product."""
    product = db.query(Product).filter(Product.sku == "TEMP-001").first()
    return product


@pytest.fixture
def test_warehouse_east(db) -> Warehouse:
    """Get the seeded east warehouse."""
    warehouse = db.query(Warehouse).filter(Warehouse.code == "EAST01").first()
    return warehouse


@pytest.fixture
def test_warehouse_west(db) -> Warehouse:
    """Get the seeded west warehouse."""
    warehouse = db.query(Warehouse).filter(Warehouse.code == "WEST01").first()
    return warehouse
