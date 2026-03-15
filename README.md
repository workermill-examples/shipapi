# ShipAPI

[![CI](https://github.com/workermill-examples/shipapi/workflows/CI/badge.svg)](https://github.com/workermill-examples/shipapi/actions)
![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Production-grade inventory management REST API with FastAPI, PostgreSQL, JWT authentication, and full-text search.

**Live Demo:** [https://shipapi.workermill.com](https://shipapi.workermill.com)

Built by [WorkerMill](https://workermill.com) — Autonomous AI software development

## Features

- 🔐 **Dual Authentication** — JWT tokens + API keys
- 🔍 **Full-text Search** — PostgreSQL TSVECTOR with relevance ranking
- 🏢 **Multi-tenant Architecture** — Organization-scoped data isolation
- 📦 **Inventory Management** — Products, categories, warehouses, stock levels
- 🔄 **Atomic Stock Transfers** — ACID-compliant warehouse transfers
- 📊 **Audit Logging** — Complete activity tracking
- 🚦 **Rate Limiting** — Per-endpoint request throttling
- 📚 **OpenAPI Documentation** — Auto-generated Swagger/ReDoc
- ✅ **Comprehensive Tests** — Unit + E2E workflow coverage
- 🐳 **Docker Ready** — Multi-stage builds, <200MB images

## Demo Credentials

**Admin Access:**
- Email: `demo@workermill.com`
- Password: `demo1234`

## Quick Start

### Prerequisites

- Python 3.13
- Docker & Docker Compose
- uv (Python package manager)

### Local Development

```bash
# Clone repository
git clone https://github.com/workermill-examples/shipapi.git
cd shipapi

# Start PostgreSQL
docker compose down --remove-orphans
docker compose up -d --wait

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run alembic upgrade head

# Seed demo data
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run python -m seed

# Start development server
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run uvicorn src.main:app --reload --port 8000
```

API available at: http://localhost:8000
Documentation: http://localhost:8000/docs

### Quality Gates

```bash
# Linting & formatting
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy src

# Tests
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi_test uv run pytest tests/ -v
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login (returns JWT tokens) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Current user profile |
| POST | `/api/v1/auth/api-key` | Generate API key |
| DELETE | `/api/v1/auth/api-key` | Revoke API key |

### Categories
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/categories` | List categories |
| POST | `/api/v1/categories` | Create category |
| GET | `/api/v1/categories/{id}` | Category detail |
| PUT | `/api/v1/categories/{id}` | Update category |
| DELETE | `/api/v1/categories/{id}` | Delete category |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/products` | List with search & filters |
| POST | `/api/v1/products` | Create product |
| GET | `/api/v1/products/{id}` | Product detail |
| PUT | `/api/v1/products/{id}` | Update product |
| DELETE | `/api/v1/products/{id}` | Soft-delete product |

### Warehouses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/warehouses` | List warehouses |
| POST | `/api/v1/warehouses` | Create warehouse |
| GET | `/api/v1/warehouses/{id}` | Warehouse detail |
| PUT | `/api/v1/warehouses/{id}` | Update warehouse |
| DELETE | `/api/v1/warehouses/{id}` | Delete warehouse |

### Stock Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/stock` | List stock levels |
| GET | `/api/v1/stock/alerts` | Low-stock alerts |
| PUT | `/api/v1/stock/adjust` | Set stock level |
| POST | `/api/v1/stock/transfers` | Transfer stock between warehouses |
| GET | `/api/v1/stock/transfers` | Transfer history |

### Audit & Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/audit` | Audit log (admin only) |
| GET | `/api/v1/health` | Health check |
| GET | `/showcase/stats` | Public stats (no auth) |

## Architecture

### Tech Stack
- **Backend:** FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Auth:** PyJWT, bcrypt, dual JWT/API key support
- **Search:** PostgreSQL TSVECTOR with GIN indexes
- **Testing:** pytest, httpx, real PostgreSQL integration
- **Deployment:** Docker, Railway, Neon PostgreSQL

### Database Schema
- **Users** — Authentication & authorization
- **Categories** — Hierarchical product categorization
- **Products** — Inventory items with full-text search
- **Warehouses** — Storage locations
- **Stock Levels** — Current inventory quantities
- **Stock Transfers** — Inventory movement history
- **Audit Logs** — Complete activity tracking

### Key Features
- **Full-text Search:** PostgreSQL TSVECTOR with `ts_rank` relevance
- **Atomic Transfers:** `SELECT FOR UPDATE` with transaction isolation
- **Rate Limiting:** slowapi with Redis-backed storage
- **Audit Trail:** Comprehensive logging of all write operations
- **Multi-tenancy:** Organization-scoped data isolation

## Contributing

This is a showcase project demonstrating WorkerMill's autonomous development capabilities. The codebase is production-ready and follows industry best practices for API development, testing, and deployment.

## License

MIT License - see LICENSE file for details.

---

**Built by [WorkerMill](https://workermill.com) — Autonomous AI Software Development**