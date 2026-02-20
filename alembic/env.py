import asyncio
import os
import ssl as _ssl
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import all models so Alembic autogenerate can detect them
from src.models import (  # noqa: F401
    AuditLog,
    Category,
    Product,
    StockLevel,
    StockTransfer,
    User,
    Warehouse,
)
from src.models.base import Base

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# Interpret the config file for Python logging (if present)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


def _asyncpg_connect_args(url: str) -> tuple[str, dict]:
    """Strip ``sslmode`` from URL and return connect_args for asyncpg."""
    parts = urlsplit(url)
    qs = parse_qs(parts.query)
    connect_args: dict = {}
    if "sslmode" in qs:
        mode = qs.pop("sslmode")[0]
        if mode in ("require", "verify-ca", "verify-full"):
            connect_args["ssl"] = _ssl.create_default_context()
        url = urlunsplit(parts._replace(query=urlencode(qs, doseq=True)))
    return url, connect_args


def get_url() -> str:
    """Return the direct (non-pooled) database URL for DDL migrations.

    PgBouncer in transaction mode cannot execute DDL, so Alembic migrations
    must use DATABASE_URL_DIRECT (the non-pooled Neon connection string).
    """
    url = os.environ["DATABASE_URL_DIRECT"]
    # Ensure the URL uses the asyncpg driver for async execution
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no DB connection).

    This allows generating SQL scripts without a live database connection.
    Uses synchronous URL rendering — asyncpg driver prefix is stripped back
    to plain postgresql for offline SQL generation.
    """
    url = get_url().replace("postgresql+asyncpg://", "postgresql://")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine (required for asyncpg)."""
    url, connect_args = _asyncpg_connect_args(get_url())
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
