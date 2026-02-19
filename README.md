# ShipAPI

**Inventory management REST API showcase** — async FastAPI, SQLAlchemy 2, and PostgreSQL.

[![Built by WorkerMill](https://img.shields.io/badge/Built%20by-WorkerMill-5865F2?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0id2hpdGUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiByeD0iMyIgZmlsbD0iIzU4NjVGMiIvPjwvc3ZnPg==)](https://workermill.com)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## Live Demo

| Resource | URL |
|----------|-----|
| Swagger UI | https://shipapi.up.railway.app/docs |
| ReDoc | https://shipapi.up.railway.app/redoc |
| Health check | https://shipapi.up.railway.app/api/v1/health |

## Demo Credentials

Use these credentials to explore the live API via Swagger UI:

| Field | Value |
|-------|-------|
| Email | `demo@workermill.com` |
| Password | `demo1234` |
| API Key | `sk_demo_shipapi_2026_showcase_key` |
| Role | `admin` (full access) |

**How to authenticate in Swagger UI:**
1. Open `/docs` and click the **Authorize** button (top right)
2. For **Bearer JWT**: POST `/api/v1/auth/login` first, copy the `access_token`, then enter `Bearer <token>` in the `HTTPBearer` field
3. For **API Key**: enter `sk_demo_shipapi_2026_showcase_key` directly in the `APIKeyHeader` field

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/workermill-examples/shipapi.git
cd shipapi

# 2. Start PostgreSQL
docker compose up -d

# 3. Install dependencies
uv sync

# 4. Configure environment
cp .env.example .env          # defaults point at the Docker container — no edits needed

# 5. Run migrations
alembic upgrade head

# 6. Seed demo data
python -m seed

# 7. Start the server
uvicorn src.main:app --reload
```

The API is now available at **http://localhost:8000**.
Interactive docs: http://localhost:8000/docs

---

## API Reference

All routes are mounted under `/api/v1`. Responses use a consistent JSON envelope.

### Authentication

Two schemes are supported — use either on any protected endpoint:

| Scheme | Header | Example |
|--------|--------|---------|
| Bearer JWT | `Authorization` | `Authorization: Bearer eyJ...` |
| API Key | `X-API-Key` | `X-API-Key: sk_demo_shipapi_2026_showcase_key` |

### Endpoints

#### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/health` | None | Liveness probe. Executes `SELECT 1` and returns `status`, `database`, `version`, `built_by`. Always HTTP 200. |

#### Auth

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|-----------|-------------|
| `POST` | `/api/v1/auth/register` | None | 5/min/IP | Register a new user. Returns profile + one-time `api_key`. 409 if email taken. |
| `POST` | `/api/v1/auth/login` | None | 10/min/IP | Authenticate with email + password. Returns `access_token` (30 min) + `refresh_token` (7 days). |
| `POST` | `/api/v1/auth/refresh` | None | 30/min/IP | Exchange a refresh token for a new token pair. Single-use; rejects access tokens. |
| `GET` | `/api/v1/auth/me` | Required | 100/min/user | Return the current user's profile. |

#### Categories

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/categories` | None | Paginated list of all categories. Query: `page`, `per_page`. Hierarchy expressed via `parent_id`. |
| `POST` | `/api/v1/categories` | Admin | Create a category. Optional `parent_id` for subcategories. |
| `GET` | `/api/v1/categories/{id}` | None | Single category with its associated products. |
| `PUT` | `/api/v1/categories/{id}` | Admin | Partial update — only sent fields are modified. |
| `DELETE` | `/api/v1/categories/{id}` | Admin | Delete category. 400 if products are still assigned (cascade protection). |

#### Products

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/products` | None | Paginated, filterable, full-text searchable product list. Query: `page`, `per_page`, `search`, `category_id`, `min_price`, `max_price`, `is_active`, `sort_by`, `sort_order`. |
| `POST` | `/api/v1/products` | Required | Create a product. 409 if SKU duplicate. |
| `GET` | `/api/v1/products/{id}` | None | Full product detail including per-warehouse stock levels. |
| `PUT` | `/api/v1/products/{id}` | Required | Partial update with audit logging of changed fields only. |
| `DELETE` | `/api/v1/products/{id}` | Admin | Soft-delete: sets `is_active=false`. References in stock/transfers/audit remain intact. |

#### Warehouses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/warehouses` | Required | Paginated list of all warehouses. Query: `page`, `per_page`. |
| `POST` | `/api/v1/warehouses` | Admin | Create a warehouse with `name`, `location`, `capacity`. |
| `GET` | `/api/v1/warehouses/{id}` | Required | Warehouse detail with computed stock summary: `total_products`, `total_quantity`, `capacity_utilization_pct`. |
| `PUT` | `/api/v1/warehouses/{id}` | Admin | Update warehouse fields. Can toggle `is_active`. |
| `GET` | `/api/v1/warehouses/{id}/stock` | Required | Paginated stock levels for a specific warehouse. |

#### Stock

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `PUT` | `/api/v1/stock/{product_id}/{warehouse_id}` | Required | Upsert stock level for a product/warehouse pair. Body: `quantity`, optional `min_threshold`. 400 if warehouse is inactive. |
| `POST` | `/api/v1/stock/transfer` | Required | Atomic transfer between two warehouses using `SELECT FOR UPDATE`. 400 `INSUFFICIENT_STOCK` if quantity is too low. |
| `GET` | `/api/v1/stock/alerts` | Required | Paginated list of stock levels below their `min_threshold`, sorted by largest shortfall first. |

#### Audit Log

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/audit-log` | Admin | Paginated audit trail. Filters: `start_date`, `end_date`, `action`, `resource_type`, `user_id`. Ordered newest-first. |

### Pagination

All list endpoints return a consistent envelope:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

### Error Responses

All errors return a consistent JSON envelope:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Product not found",
    "details": []
  }
}
```

Common error codes: `NOT_FOUND`, `CONFLICT`, `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `RATE_LIMIT_EXCEEDED`, `INSUFFICIENT_STOCK`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Railway                                 │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     Docker Container                      │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │                  FastAPI (uvicorn)                  │  │  │
│  │  │                                                     │  │  │
│  │  │  RequestIdMiddleware → AccessLogMiddleware → CORS   │  │  │
│  │  │                          │                         │  │  │
│  │  │            ┌─────────────┴──────────────┐          │  │  │
│  │  │            │         API Routers         │          │  │  │
│  │  │            │  /auth  /categories         │          │  │  │
│  │  │            │  /products  /warehouses     │          │  │  │
│  │  │            │  /stock  /audit-log         │          │  │  │
│  │  │            └─────────────┬──────────────┘          │  │  │
│  │  │                          │                         │  │  │
│  │  │            ┌─────────────┴──────────────┐          │  │  │
│  │  │            │         Services            │          │  │  │
│  │  │            │  auth  stock  audit         │          │  │  │
│  │  │            └─────────────┬──────────────┘          │  │  │
│  │  │                          │                         │  │  │
│  │  │            ┌─────────────┴──────────────┐          │  │  │
│  │  │            │   SQLAlchemy 2 (asyncpg)    │          │  │  │
│  │  └────────────┴─────────────────────────────┴──────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│              pre-deploy: alembic upgrade head                    │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │        Neon          │
                    │  (serverless Postgres│
                    │   16, pool + direct) │
                    └─────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.13 |
| Framework | FastAPI | ≥ 0.115 |
| ASGI Server | Uvicorn | ≥ 0.32 |
| ORM | SQLAlchemy (async) | ≥ 2.0 |
| DB Driver | asyncpg | ≥ 0.29 |
| Migrations | Alembic | ≥ 1.13 |
| Validation | Pydantic v2 | ≥ 2.0 |
| Config | pydantic-settings | ≥ 2.6 |
| Auth | python-jose (JWT) + bcrypt | ≥ 3.3 / ≥ 4.0 |
| Rate Limiting | slowapi | ≥ 0.1.9 |
| Database | PostgreSQL | 16 |
| Package Manager | uv | latest |
| Linter/Formatter | ruff | ≥ 0.8 |
| Type Checker | mypy (strict) | ≥ 1.13 |
| Testing | pytest + httpx | ≥ 8.3 / ≥ 0.27 |
| Coverage | coverage | ≥ 7.6 |
| Containerization | Docker | multi-stage |
| Hosting | Railway | — |
| Production DB | Neon (serverless) | — |

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage report (must stay ≥ 80%)
coverage run -m pytest
coverage report

# Run a single test file
pytest tests/test_main.py -v

# Run a single test
pytest tests/test_main.py::test_startup -v
```

Tests use `httpx.AsyncClient` against an in-memory test database. Environment defaults are
set in `tests/conftest.py` so tests run without a `.env` file.

### Code Quality

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src
```

---

## Deployment

### Railway (automatic)

Pushes to `main` trigger automatic deployments on Railway:

1. **Build** — Docker multi-stage build (`python:3.13-slim` → non-root `appuser`)
2. **Pre-deploy** — `alembic upgrade head` runs migrations before traffic switches
3. **Health check** — Railway polls `GET /api/v1/health` (300 s timeout) before marking healthy
4. **Restart policy** — On failure, max 3 retries

### Environment Variables

Set these in Railway's environment variables dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Pooled Neon URL (`postgresql+asyncpg://...?sslmode=require`) |
| `DATABASE_URL_DIRECT` | Yes | Direct Neon URL for Alembic migrations |
| `JWT_SECRET_KEY` | Yes | Long random secret — generate with `openssl rand -hex 32` |
| `JWT_ALGORITHM` | No | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Default: `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | Default: `7` |

**Generate a JWT secret:**
```bash
openssl rand -hex 32
```

### Neon PostgreSQL

Production uses Neon serverless PostgreSQL. Two connection strings are required:

- **`DATABASE_URL`** — PgBouncer pooled URL (used by the app; `pool_pre_ping=True` handles connection reuse after scale-to-zero)
- **`DATABASE_URL_DIRECT`** — Direct URL (used by Alembic; PgBouncer is incompatible with migration session mode)

### Local Development

The `docker-compose.yml` starts `postgres:16-alpine` on `localhost:5432`:

```
User:     shipapi
Password: password
Database: shipapi
```

`.env.example` defaults point at this container — copy it and you're ready:

```bash
cp .env.example .env
```

---

## Project Structure

```
shipapi/
├── src/
│   ├── api/
│   │   ├── router.py        # Mounts all sub-routers under /api/v1
│   │   ├── health.py        # GET /health
│   │   ├── auth.py          # register, login, refresh, me
│   │   ├── categories.py    # CRUD categories
│   │   ├── products.py      # CRUD products, full-text search
│   │   ├── warehouses.py    # CRUD warehouses + stock summary
│   │   ├── stock.py         # upsert, transfer, alerts
│   │   └── audit.py         # GET /audit-log
│   ├── middleware/
│   │   ├── access_log.py    # Structured JSON access logging
│   │   ├── error_handler.py # Unified error envelope
│   │   ├── rate_limit.py    # slowapi wiring + key functions
│   │   └── request_id.py    # X-Request-Id on every request
│   ├── models/              # SQLAlchemy ORM models (7 tables)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic (auth, stock, audit)
│   ├── config.py            # pydantic-settings env var config
│   ├── database.py          # Async engine, session factory, get_db
│   ├── dependencies.py      # get_current_user, require_admin
│   └── main.py              # FastAPI app, middleware, lifespan
├── alembic/                 # Migration scripts
├── seed/                    # Demo data seed script
├── tests/                   # pytest test suite
├── .env.example             # Environment template
├── docker-compose.yml       # Local PostgreSQL
├── Dockerfile               # Multi-stage production build
├── railway.toml             # Railway deployment config
└── pyproject.toml           # Dependencies and tool config
```

---

## Seed Data

The `seed/` module populates the database with realistic demo data:

```bash
python -m seed
```

| Data | Count | Notes |
|------|-------|-------|
| Admin user | 1 | `demo@workermill.com` / `demo1234` |
| Categories | 20 | 5 top-level + 15 subcategories |
| Products | 50 | 45 active + 5 inactive; rich descriptions for full-text search testing |

The script is **idempotent** — safe to run multiple times. It checks for existing records
before inserting (by email, category name, and SKU).

**SKU format:** `{CATEGORY_PREFIX}-{SUBCATEGORY_PREFIX}-{3-digit number}` (e.g., `ELEC-LAP-001`)

---

*Built by [WorkerMill](https://workermill.com)*
