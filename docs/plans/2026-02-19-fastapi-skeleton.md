# FastAPI App Skeleton, Config & Database Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the FastAPI application skeleton with pydantic-settings config, async SQLAlchemy database layer, and app entry point with lifespan, CORS, and OpenAPI tag groups.

**Architecture:** pydantic-settings loads env vars into a typed Settings object; src/database.py creates an async SQLAlchemy engine with Neon-compatible pooling and exposes a get_db dependency; src/main.py wires everything together with FastAPI lifespan, CORS middleware, and OpenAPI tag metadata.

**Tech Stack:** FastAPI, pydantic-settings, SQLAlchemy 2.x async, asyncpg, pytest-asyncio, httpx

---

### Task 1: src/__init__.py — package marker

**Files:**
- Modify: `src/__init__.py`

**Step 1: Write minimal package marker (no test needed — it's just a package init)**

```python
# ShipAPI package
```

**Step 2: Commit**

```bash
git add src/__init__.py
git commit -m "feat: add src package init"
```

---

### Task 2: src/config.py — typed settings via pydantic-settings

**Files:**
- Modify: `src/config.py` (create)
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

```python
import pytest
from pydantic import ValidationError


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    from importlib import reload
    import src.config as cfg_module
    with pytest.raises((ValidationError, Exception)):
        cfg_module.Settings()


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "supersecret")
    from src.config import Settings
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@localhost/db"
    assert s.jwt_secret_key == "supersecret"
    assert s.app_name == "ShipAPI"
    assert s.version == "1.0.0"
    assert s.debug is False
    assert s.access_token_expire_minutes == 30
    assert s.refresh_token_expire_days == 7


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "supersecret")
    from src.config import Settings
    s = Settings()
    assert s.database_url_direct is None
    assert s.jwt_algorithm == "HS256"
```

**Step 2: Run test to verify it fails**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && uv run pytest tests/test_config.py -v 2>&1 | head -40
```

Expected: ImportError or ModuleNotFoundError for `src.config`

**Step 3: Write implementation**

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str
    database_url_direct: str | None = None

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # App
    app_name: str = "ShipAPI"
    version: str = "1.0.0"
    debug: bool = False


settings = Settings()
```

**Step 4: Run tests to verify they pass**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && DATABASE_URL=postgresql+asyncpg://u:p@localhost/db JWT_SECRET_KEY=secret uv run pytest tests/test_config.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add pydantic-settings config"
```

---

### Task 3: src/database.py — async SQLAlchemy engine + session factory

**Files:**
- Create: `src/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, patch


def test_engine_is_created(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    from src.database import engine
    assert engine is not None


def test_async_session_factory(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    from src.database import AsyncSessionLocal
    assert AsyncSessionLocal is not None


@pytest.mark.asyncio
async def test_get_db_yields_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    from src.database import get_db
    # get_db is an async generator — just verify it's callable
    gen = get_db()
    assert hasattr(gen, "__anext__")
```

**Step 2: Run test to verify it fails**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && DATABASE_URL=postgresql+asyncpg://u:p@localhost/db JWT_SECRET_KEY=secret uv run pytest tests/test_database.py -v 2>&1 | head -40
```

Expected: ImportError (src.database doesn't exist yet)

**Step 3: Write implementation**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

**Step 4: Run tests to verify they pass**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && DATABASE_URL=postgresql+asyncpg://u:p@localhost/db JWT_SECRET_KEY=secret uv run pytest tests/test_database.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add async SQLAlchemy engine and session factory"
```

---

### Task 4: src/main.py — FastAPI app with lifespan, CORS, and OpenAPI tags

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py`

**Step 1: Write the failing test**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_db_connect():
    with patch("src.main.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_engine.dispose = AsyncMock()
        yield mock_engine


@pytest.mark.asyncio
async def test_openapi_json_returns_200(mock_db_connect, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "ShipAPI"
    assert data["info"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_openapi_has_expected_tags(mock_db_connect, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/openapi.json")
    tag_names = {t["name"] for t in response.json()["tags"]}
    assert tag_names == {"Health", "Auth", "Categories", "Products", "Warehouses", "Stock", "Audit"}


@pytest.mark.asyncio
async def test_docs_endpoint_returns_200(mock_db_connect, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cors_headers_present(mock_db_connect, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    from src.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/openapi.json",
            headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"},
        )
    assert "access-control-allow-origin" in response.headers
```

**Step 2: Run test to verify it fails**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && DATABASE_URL=postgresql+asyncpg://u:p@localhost/db JWT_SECRET_KEY=secret uv run pytest tests/test_main.py -v 2>&1 | head -40
```

Expected: ImportError for `src.main`

**Step 3: Write implementation**

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: verify DB connection
    async with engine.connect() as conn:
        await conn.run_sync(lambda _: None)
    yield
    # Shutdown: dispose engine
    await engine.dispose()


openapi_tags = [
    {"name": "Health", "description": "Health check endpoints"},
    {"name": "Auth", "description": "Authentication and authorization"},
    {"name": "Categories", "description": "Product category management"},
    {"name": "Products", "description": "Product catalog management"},
    {"name": "Warehouses", "description": "Warehouse management"},
    {"name": "Stock", "description": "Stock level management"},
    {"name": "Audit", "description": "Audit log access"},
]

app = FastAPI(
    title="ShipAPI",
    description="Inventory management REST API showcase",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Step 4: Run tests to verify they pass**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && DATABASE_URL=postgresql+asyncpg://u:p@localhost/db JWT_SECRET_KEY=secret uv run pytest tests/test_main.py -v
```

Expected: All PASS

**Step 5: Verify ruff passes**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && uv run ruff check src/ && uv run ruff format --check src/
```

Expected: No errors

**Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add FastAPI app skeleton with lifespan and CORS"
```

---

### Task 5: Final validation

**Step 1: Run all tests**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && DATABASE_URL=postgresql+asyncpg://u:p@localhost/db JWT_SECRET_KEY=secret uv run pytest tests/ -v
```

Expected: All PASS

**Step 2: Run ruff on entire src/**

```bash
cd /tmp/workermill-3f28895f-e0f7-499f-a071-6e5d5b7518db/worktrees/story-2 && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
```

Expected: No errors
