# ShipAPI — Developer Reference

Inventory management REST API showcase built with FastAPI, SQLAlchemy (async), and PostgreSQL.

---

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Start local database
docker compose up -d

# 3. Copy env file and fill in values
cp .env.example .env

# 4. Run migrations
alembic upgrade head

# 5. Start dev server
uvicorn src.main:app --reload
```

API docs available at http://localhost:8000/docs

---

## Command Reference

| Task        | Command                                      | Notes                                         |
|-------------|----------------------------------------------|-----------------------------------------------|
| Install     | `uv sync`                                    | Installs all deps from `uv.lock`              |
| Install dev | `uv sync --dev` (or `uv sync` — auto-includes dev deps) | Dev extras defined in `pyproject.toml` |
| Run         | `uvicorn src.main:app --reload`              | Hot-reload on file changes                    |
| Migrate     | `alembic upgrade head`                       | Apply all pending migrations                  |
| Rollback    | `alembic downgrade -1`                       | Roll back one migration                       |
| Seed        | `python -m seed` *(coming soon)*             | Populate dev data                             |
| Test        | `pytest`                                     | Runs all tests in `tests/`                    |
| Test + cov  | `coverage run -m pytest && coverage report`  | Must stay ≥ 80 % (`fail_under = 80`)          |
| Lint        | `ruff check .`                               | Checks `src/` and `tests/`                    |
| Format      | `ruff format .`                              | Auto-formats (100-char line length)           |
| Format check| `ruff format --check .`                      | CI-safe format check (no writes)              |
| Typecheck   | `mypy src`                                   | Strict mypy with pydantic plugin              |

---

## Local Development

### Prerequisites

- Python 3.13 ([`.python-version`](.python-version) is read by `pyenv` / `uv` automatically)
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- Docker + Docker Compose (for the local PostgreSQL instance)

### Step-by-Step Setup

1. **Clone the repo** and enter the directory.

2. **Install Python dependencies:**
   ```bash
   uv sync
   ```
   This reads `uv.lock` exactly — no version drift.

3. **Start PostgreSQL:**
   ```bash
   docker compose up -d
   ```
   This starts `postgres:16-alpine` on `localhost:5432` with:
   - User: `shipapi`  Password: `password`  DB: `shipapi`

4. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   ```
   The defaults in `.env.example` point at the Docker container — no edits needed for local dev.

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the server:**
   ```bash
   uvicorn src.main:app --reload
   ```

7. **Verify everything works:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

### Running Tests

```bash
# Run all tests
pytest

# With coverage report
coverage run -m pytest
coverage report

# Single test file
pytest tests/test_main.py -v

# Single test
pytest tests/test_main.py::test_startup -v
```

Tests require environment variables to be set. The `tests/conftest.py` fixture sets safe
defaults so test collection succeeds without a `.env` file. Individual tests use `monkeypatch`
for scenario-specific overrides.

---

## Environment Variables

All variables are loaded by `src/config.py` via `pydantic-settings`. Copy `.env.example` to
`.env` — the file is gitignored and never committed.

| Variable                         | Required | Default  | Description                                                     |
|----------------------------------|----------|----------|-----------------------------------------------------------------|
| `DATABASE_URL`                   | Yes      | —        | Async PostgreSQL URL (`postgresql+asyncpg://...`). Used by the app for all queries. Use the pooled (PgBouncer) URL on Neon. |
| `DATABASE_URL_DIRECT`            | No       | `None`   | Direct PostgreSQL URL, bypassing PgBouncer. Used by Alembic for migrations. Required on Neon. |
| `JWT_SECRET_KEY`                 | Yes      | —        | Secret for signing JWT tokens. Generate with `openssl rand -hex 32`. |
| `JWT_ALGORITHM`                  | No       | `HS256`  | JWT signing algorithm.                                          |
| `ACCESS_TOKEN_EXPIRE_MINUTES`    | No       | `30`     | Access token lifetime in minutes.                               |
| `REFRESH_TOKEN_EXPIRE_DAYS`      | No       | `7`      | Refresh token lifetime in days.                                 |
| `APP_NAME`                       | No       | `ShipAPI`| Application name shown in OpenAPI docs.                         |
| `VERSION`                        | No       | `1.0.0`  | Application version.                                            |
| `DEBUG`                          | No       | `false`  | Enable debug mode.                                              |
| `PORT`                           | No       | `8000`   | Server port. Set automatically by Railway at deploy time.       |

**Local dev values** (from `docker-compose.yml`):

```env
DATABASE_URL=postgresql+asyncpg://shipapi:password@localhost:5432/shipapi
DATABASE_URL_DIRECT=postgresql+asyncpg://shipapi:password@localhost:5432/shipapi
JWT_SECRET_KEY=dev-secret-key-change-in-production
```

---

## Conventions

### API

- **Prefix:** all routes are mounted under `/api/v1/`
- **Docs:** Swagger UI at `/docs`, ReDoc at `/redoc`
- **OpenAPI tags** define 7 endpoint groups: Health, Auth, Categories, Products, Warehouses, Stock, Audit

### Primary Keys

All tables use **UUID v4** primary keys (`uuid` type in PostgreSQL).

```python
import uuid
id: uuid.UUID = Field(default_factory=uuid.uuid4)
```

### Async SQLAlchemy

All database access is **async**. Use the `get_db` dependency to obtain a session:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db

@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db)):
    ...
```

The engine is configured with `pool_pre_ping=True` — this is **critical** for Neon serverless
PostgreSQL, which scales to zero between requests and will drop idle connections.

### Error Response Format

All errors return a consistent JSON envelope:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors FastAPI returns HTTP 422 with field-level detail from Pydantic.

### Pagination Format

List endpoints return a consistent paginated envelope:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

Query parameters: `?page=1&size=20` (default page=1, size=20).

### Audit Logging

All mutating operations (create, update, delete) on core resources write an audit record.
The `Audit` tag exposes read-only access to this log.

### Code Style

- Line length: **100 characters** (enforced by `ruff`)
- Target: **Python 3.13** — use modern syntax (`X | Y` unions, `type` aliases, etc.)
- Imports sorted by `ruff` with `src` as first-party
- Type annotations are **mandatory** everywhere (`mypy --strict`)

---

## Project Structure

```
shipapi/
├── src/
│   ├── __init__.py          # Package root
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # Async engine, session factory, get_db
│   └── main.py              # FastAPI app, lifespan, CORS, router registration
├── alembic/                 # Migration scripts (added in later cards)
├── seed/                    # Seed data scripts (added in later cards)
├── tests/
│   ├── conftest.py          # Shared fixtures and env defaults
│   ├── test_config.py
│   ├── test_database.py
│   └── test_main.py
├── docs/
│   └── plans/               # Implementation plans
├── .env.example             # Environment template (committed)
├── .env                     # Local secrets (gitignored)
├── pyproject.toml           # Dependencies, ruff, mypy, pytest, coverage config
├── uv.lock                  # Locked dependency graph
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Local PostgreSQL
├── railway.toml             # Railway deployment config
└── CLAUDE.md                # This file
```

---

## Deployment

### Railway

The project deploys to [Railway](https://railway.app/) automatically from the `main` branch.

| Setting             | Value                                       |
|---------------------|---------------------------------------------|
| Builder             | Dockerfile                                  |
| Health check path   | `/api/v1/health`                            |
| Health check timeout| 300 seconds                                 |
| Restart policy      | On failure (max 3 retries)                  |
| Pre-deploy command  | `alembic upgrade head`                      |
| Port                | Set by Railway via `$PORT` env var          |

The `CMD` in the Dockerfile uses `sh -c` to expand `${PORT:-8000}` at container start time,
which is required for Railway's dynamic port injection.

### Database

Production uses [Neon](https://neon.tech/) serverless PostgreSQL:

- **`DATABASE_URL`** — pooled connection via PgBouncer (for the app)
- **`DATABASE_URL_DIRECT`** — direct connection (for Alembic migrations, which are incompatible with PgBouncer in session mode)

Set both in Railway's environment variables dashboard.

### Generate a JWT Secret

```bash
openssl rand -hex 32
```

Paste the output into `JWT_SECRET_KEY` in Railway's environment variables.
