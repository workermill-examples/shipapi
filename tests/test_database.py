import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.database import AsyncSessionLocal, engine, get_db


def test_engine_is_async_engine():
    assert isinstance(engine, AsyncEngine)


def test_engine_has_pool_settings():
    pool = engine.pool
    assert pool.size() == 5  # type: ignore[attr-defined]


def test_async_session_factory_is_sessionmaker():
    assert isinstance(AsyncSessionLocal, async_sessionmaker)


@pytest.mark.asyncio
async def test_get_db_is_async_generator():
    gen = get_db()
    assert hasattr(gen, "__anext__")
    await gen.aclose()
