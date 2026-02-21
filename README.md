# ShipAPI

**An inventory management REST API built entirely by AI agents.**

ShipAPI is a showcase application demonstrating [WorkerMill](https://workermill.com) — an autonomous AI coding platform that takes Jira/Linear/GitHub tickets and ships production code. Every line of code in this repository was written, tested, and deployed by WorkerMill's AI workers.

[Live Demo](https://shipapi.workermill.com/docs) | [WorkerMill Platform](https://workermill.com) | [Documentation](https://workermill.com/docs)

[![CI](https://github.com/workermill-examples/shipapi/actions/workflows/ci.yml/badge.svg)](https://github.com/workermill-examples/shipapi/actions/workflows/ci.yml)
[![Deploy](https://github.com/workermill-examples/shipapi/actions/workflows/deploy.yml/badge.svg)](https://github.com/workermill-examples/shipapi/actions/workflows/deploy.yml)

---

## What's Inside

ShipAPI is a real, functional inventory management API — not a toy demo. It includes:

- **Product Catalog** — Categories with subcategories, full-text search, filtering, and sorting
- **Warehouse Management** — Multi-warehouse stock tracking with capacity utilization metrics
- **Stock Operations** — Atomic inter-warehouse transfers using `SELECT FOR UPDATE`
- **Threshold Alerts** — Stock-below-minimum alerting sorted by largest shortfall
- **JWT + API Key Auth** — Dual authentication with role-based access control (admin/user)
- **Rate Limiting** — Per-endpoint rate limits with IP and user-based throttling
- **Audit Trail** — Full audit log of every data mutation with field-level change tracking
- **Request Tracing** — `X-Request-Id` on every request, structured JSON access logs
- **Interactive Docs** — Auto-generated Swagger UI and ReDoc

## How It Was Built

ShipAPI was created across multiple WorkerMill task runs (called "epics"), each triggered by tickets on a project board:

| Epic | Stories | What Was Built |
|------|---------|----------------|
| SA-1 | 8 | Project scaffolding, SQLAlchemy models, Alembic migrations, auth system, Docker, CI/CD |
| SA-2 | 7 | Category/product CRUD, full-text search, warehouse management, stock operations |
| SA-3 | 6 | Stock transfers, threshold alerts, audit logging, rate limiting, request middleware |
| SA-4 | 5 | Seed data, demo credentials, Neon PostgreSQL, Railway deployment, smoke tests |
| SA-5 | 4 | Comprehensive test suite — 344 tests, mypy strict mode, coverage enforcement |

Each epic was planned by a WorkerMill planner agent, decomposed into parallel stories, executed by specialist AI personas (backend developer, database administrator, QA engineer), reviewed by a tech lead agent, and consolidated into a single PR.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| Framework | FastAPI ≥ 0.115 |
| ORM | SQLAlchemy 2 (async) + asyncpg |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | python-jose (JWT) + bcrypt |
| Rate Limiting | slowapi |
| Testing | pytest + httpx (344 tests) |
| Type Checker | mypy (strict mode) |
| Package Manager | uv |
| Linter/Formatter | ruff |
| Database | PostgreSQL 16 (Neon serverless) |
| Hosting | Railway |
| CI/CD | GitHub Actions |

## Try the Demo

Visit the [Swagger UI](https://shipapi.workermill.com/docs) or [ReDoc](https://shipapi.workermill.com/redoc) to explore the live API.

| | |
|-|-|
| **Email** | demo@workermill.com |
| **Password** | demo1234 |
| **API Key** | `sk_demo_shipapi_2026_showcase_key` |

**How to authenticate in Swagger UI:**
1. Open `/docs` and click the **Authorize** button (top right)
2. For **Bearer JWT**: POST `/api/v1/auth/login` first, copy the `access_token`, then enter `Bearer <token>` in the `HTTPBearer` field
3. For **API Key**: enter `sk_demo_shipapi_2026_showcase_key` directly in the `APIKeyHeader` field

## Run Locally

```bash
git clone https://github.com/workermill-examples/shipapi.git
cd shipapi
```

Create `.env`:

```bash
cp .env.example .env    # defaults point at the Docker container — no edits needed
```

Set up the database and start:

```bash
docker compose up -d
uv sync
alembic upgrade head
python -m seed
uvicorn src.main:app --reload
```

Open [localhost:8000/docs](http://localhost:8000/docs).

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
| `GET` | `/api/v1/health` | None | Liveness probe. Returns `status`, `database`, `version`, `built_by`. |

#### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | None | Register a new user. Returns profile + one-time `api_key`. |
| `POST` | `/api/v1/auth/login` | None | Authenticate with email + password. Returns JWT token pair. |
| `POST` | `/api/v1/auth/refresh` | None | Exchange a refresh token for a new token pair. |
| `GET` | `/api/v1/auth/me` | Required | Return the current user's profile. |

#### Categories

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/categories` | None | Paginated list with hierarchy via `parent_id`. |
| `POST` | `/api/v1/categories` | Admin | Create a category. Optional `parent_id` for subcategories. |
| `GET` | `/api/v1/categories/{id}` | None | Single category with associated products. |
| `PUT` | `/api/v1/categories/{id}` | Admin | Partial update. |
| `DELETE` | `/api/v1/categories/{id}` | Admin | Delete. 400 if products still assigned. |

#### Products

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/products` | None | Paginated, filterable, full-text searchable. |
| `POST` | `/api/v1/products` | Required | Create a product. 409 if SKU duplicate. |
| `GET` | `/api/v1/products/{id}` | None | Detail including per-warehouse stock levels. |
| `PUT` | `/api/v1/products/{id}` | Required | Partial update with audit logging. |
| `DELETE` | `/api/v1/products/{id}` | Admin | Soft-delete: sets `is_active=false`. |

#### Warehouses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/warehouses` | Required | Paginated list. |
| `POST` | `/api/v1/warehouses` | Admin | Create with `name`, `location`, `capacity`. |
| `GET` | `/api/v1/warehouses/{id}` | Required | Detail with stock summary and capacity utilization. |
| `PUT` | `/api/v1/warehouses/{id}` | Admin | Update fields. |
| `GET` | `/api/v1/warehouses/{id}/stock` | Required | Paginated stock levels. |

#### Stock

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `PUT` | `/api/v1/stock/{product_id}/{warehouse_id}` | Required | Upsert stock level. |
| `POST` | `/api/v1/stock/transfer` | Required | Atomic transfer between warehouses. |
| `GET` | `/api/v1/stock/alerts` | Required | Stock below `min_threshold`, sorted by shortfall. |

#### Audit Log

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/audit-log` | Admin | Paginated audit trail with date/action/resource filters. |

### Response Format

All list endpoints return a consistent envelope:

```json
{
  "data": [...],
  "pagination": { "page": 1, "per_page": 20, "total": 100, "total_pages": 5 }
}
```

All errors return:

```json
{
  "error": { "code": "NOT_FOUND", "message": "Product not found", "details": [] }
}
```

---

## Project Structure

```
src/
  api/                    # FastAPI routers
    router.py             # Mounts all sub-routers under /api/v1
    health.py             # GET /health
    auth.py               # register, login, refresh, me
    categories.py         # CRUD categories
    products.py           # CRUD products, full-text search
    warehouses.py         # CRUD warehouses + stock summary
    stock.py              # upsert, transfer, alerts
    audit.py              # GET /audit-log
  middleware/             # Request pipeline
    access_log.py         # Structured JSON access logging
    error_handler.py      # Unified error envelope
    rate_limit.py         # slowapi wiring + key functions
    request_id.py         # X-Request-Id on every request
  models/                 # SQLAlchemy ORM models (7 tables)
  schemas/                # Pydantic request/response schemas
  services/               # Business logic (auth, stock, audit)
  config.py               # pydantic-settings env var config
  database.py             # Async engine, session factory, get_db
  dependencies.py         # get_current_user, require_admin
  main.py                 # FastAPI app, middleware, lifespan
alembic/                  # Migration scripts
seed/                     # Demo data seed script
tests/                    # pytest test suite (344 tests)
docker-compose.yml        # Local PostgreSQL
Dockerfile                # Multi-stage production build
railway.toml              # Railway deployment config
pyproject.toml            # Dependencies and tool config
```

## Database Schema

```
User ──< Product
  │        └──< StockLevel >── Warehouse
  │
  └──< AuditLog

Category ──< Category (self-referential via parent_id)
  └──< Product

StockLevel ──< StockTransfer
```

7 models: User, Category, Product, Warehouse, StockLevel, StockTransfer, AuditLog.

## Development

```bash
pytest                   # Run all tests
coverage run -m pytest   # Run with coverage
ruff check .             # Lint
ruff format .            # Format
mypy src                 # Type check (strict)
```

## About WorkerMill

[WorkerMill](https://workermill.com) is an autonomous AI coding platform. Point it at a ticket, and it:

1. **Plans** — Decomposes the task into parallel stories with file targets
2. **Executes** — Specialist AI personas (backend dev, database admin, QA) work in parallel
3. **Reviews** — Tech lead agent reviews each story for quality
4. **Ships** — Creates a consolidated PR with all changes

ShipAPI exists to demonstrate that WorkerMill can build and maintain a real application end-to-end. Every commit in this repo's history traces back to a WorkerMill task.

## License

MIT
