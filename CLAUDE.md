# CLAUDE.md — Developer Reference

ShipAPI is a production-grade inventory management REST API with React dashboard frontend.

## Quick Start

### Prerequisites
- Python 3.13 (pinned in `.python-version`)
- Docker & Docker Compose (for PostgreSQL)
- Node.js 20+ (for frontend)
- uv (Python package manager)

### Local Development Setup

```bash
# 1. Database
docker compose down --remove-orphans
docker compose up -d --wait

# 2. Backend dependencies
uv sync

# 3. Environment
cp .env.example .env
# Edit .env with your JWT_SECRET_KEY: openssl rand -hex 32

# 4. Database setup
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run alembic upgrade head
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run python -m seed

# 5. Run backend
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run uvicorn src.main:app --reload --port 8000

# 6. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173
Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs

## Pre-Commit Quality Gates

**MANDATORY** - Run these commands before every commit:

```bash
# Clean up database
docker compose down --remove-orphans
docker compose up -d --wait

# Backend lint & format
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type checking
uv run mypy src

# Backend tests (separate test database)
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi_test uv run pytest tests/ -v --tb=short --ignore=tests/test_e2e_workflows.py
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi_test uv run pytest tests/test_e2e_workflows.py -v --tb=short

# Cleanup
docker compose down

# Frontend lint & build
cd frontend && npm run lint
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.13
- **ORM**: SQLAlchemy 2.0 (sync with psycopg2)
- **Database**: PostgreSQL 17 (Neon in production)
- **Migrations**: Alembic
- **Validation**: Pydantic V2 + pydantic-settings
- **Auth**: JWT (PyJWT library) + API keys, bcrypt passwords
- **Rate Limiting**: slowapi
- **Testing**: pytest + FastAPI TestClient
- **Type Checking**: mypy (non-strict)
- **Linting**: ruff
- **Package Manager**: uv

### Frontend
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite 6
- **Styling**: Tailwind CSS v4 (CSS-based config)
- **UI Components**: shadcn/ui (new-york style)
- **Charts**: Recharts
- **HTTP Client**: Axios (with JWT interceptor)
- **Routing**: React Router v7
- **Icons**: Lucide React

### Infrastructure
- **Hosting**: Railway (Dockerfile deploy)
- **Database**: Neon PostgreSQL
- **CI/CD**: GitHub Actions

## Key Conventions

### Database
- **All primary keys are UUIDs** (`uuid.UUID` type in FastAPI path params)
- **Timestamps**: `created_at`, `updated_at` (always these exact names)
- **Soft delete**: Use `is_active` flag, not hard delete
- **Search**: PostgreSQL full-text search with `TSVECTOR` + GIN index

### API Design
- **Prefix**: All endpoints under `/api/v1/` (except `/showcase/stats`)
- **Pagination**: Use `PaginatedResponse` schema with `items`, `total`, `page`, `per_page`
- **Errors**: Always return `{"detail": "message"}` format
- **Headers**: Every response includes `X-Request-Id`

### Authentication
- **JWT**: Use PyJWT library (`import jwt`), never `python-jose`
- **API Keys**: `sk_` prefix, SHA-256 hashed storage
- **Dual auth**: Accept either `Authorization: Bearer <token>` or `X-API-Key: sk_...`

### Code Standards
- **Line length**: 120 characters
- **Imports**: Always import from package root (`from src.models import User`)
- **Path params**: Always type as `uuid.UUID` for model IDs
- **Datetime**: Always use `datetime.now(timezone.utc)` (never `datetime.utcnow()`)
- **Pydantic**: Use `model_config = ConfigDict(...)`, never `class Config:`

### Testing
- **Real database**: Tests run against real PostgreSQL, never SQLite/mocks
- **Test database**: `shipapi_test` (created/dropped by conftest.py)
- **E2E tests**: Complete user journeys in `test_e2e_workflows.py`

## Common Commands

### Development
```bash
# Run backend with auto-reload
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run uvicorn src.main:app --reload --port 8000

# Run frontend dev server
cd frontend && npm run dev

# Create new migration
uv run alembic revision --autogenerate -m "Description"

# Run migrations
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run alembic upgrade head

# Seed database (idempotent)
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run python -m seed

# Reset database
docker compose down --volumes && docker compose up -d --wait
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run alembic upgrade head
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi uv run python -m seed
```

### Testing
```bash
# Run all tests
docker compose up -d --wait
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi_test uv run pytest tests/ -v

# Run specific test file
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi_test uv run pytest tests/test_products.py -v

# Run with coverage
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi_test uv run pytest tests/ --cov=src --cov-report=html

# E2E workflows (run separately)
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi_test uv run pytest tests/test_e2e_workflows.py -v
```

### Code Quality
```bash
# Format code
uv run ruff format src/ tests/

# Check lint issues
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Type check
uv run mypy src

# Pre-commit hook simulation
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/ && uv run mypy src
```

### Production
```bash
# Build Docker image
docker build -t shipapi .

# Deploy to Railway (manual trigger only)
# Uses GitHub Actions workflow_dispatch

# Check production health
curl https://shipapi.workermill.com/api/v1/health
```

## Environment Variables

### Required (.env)
```bash
DATABASE_URL=postgresql://shipapi:shipapi@localhost:5432/shipapi
DATABASE_URL_DIRECT=postgresql://shipapi:shipapi@localhost:5432/shipapi
JWT_SECRET_KEY=your-64-char-hex-secret
PORT=8000
```

### Production (Railway)
- `DATABASE_URL`: Neon pooled connection
- `DATABASE_URL_DIRECT`: Neon direct connection (for migrations)
- `JWT_SECRET_KEY`: Random secret
- `PORT`: 8000

## Project Structure

```
shipapi/
├── src/                    # Backend source
│   ├── main.py            # FastAPI app + StaticFiles mount
│   ├── config.py          # Settings (DATABASE_URL, JWT_SECRET_KEY)
│   ├── database.py        # SQLAlchemy setup + get_db dependency
│   ├── auth.py            # JWT encode/decode + password hashing
│   ├── dependencies.py    # get_db, get_current_user, get_current_admin
│   ├── middleware.py      # RequestId + AccessLog middleware
│   ├── models/            # SQLAlchemy models (7 total)
│   ├── schemas/           # Pydantic schemas + PaginatedResponse
│   └── routers/           # FastAPI route handlers
├── tests/                 # Backend tests (10 files + E2E workflows)
├── frontend/              # React dashboard
│   ├── src/
│   │   ├── pages/         # Route components
│   │   ├── components/    # Reusable components + shadcn/ui
│   │   └── lib/           # API client + utilities
│   └── package.json       # Frontend dependencies
├── alembic/               # Database migrations
├── seed/                  # Database seeding script
├── docker-compose.yml     # Local PostgreSQL (port 5432)
├── Dockerfile             # Multi-stage: frontend build + backend
├── railway.toml           # Railway deployment config
└── pyproject.toml         # Python dependencies + tool config
```

## API Overview

### Authentication
- `POST /api/v1/auth/register` - Create account
- `POST /api/v1/auth/login` - Login (returns JWT tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Current user profile
- `POST /api/v1/auth/api-key` - Generate API key
- `DELETE /api/v1/auth/api-key` - Revoke API key

### Resources (CRUD)
- `/api/v1/categories` - Product categories (hierarchy support)
- `/api/v1/products` - Inventory items (full-text search, filters)
- `/api/v1/warehouses` - Storage locations
- `/api/v1/stock` - Stock levels + atomic transfers
- `/api/v1/audit` - Activity audit log

### Utilities
- `GET /api/v1/health` - Health check + DB connectivity
- `GET /showcase/stats` - Public stats for demo (no auth)

## Demo Credentials

**Admin User:**
- Email: `demo@workermill.com`
- Password: `demo1234`

Seeded data includes:
- 20 categories (5 top-level + 15 subcategories)
- 50 products (45 active + 5 inactive)
- 3 warehouses
- 150+ stock records
- 20 stock transfers
- 50+ audit entries

## Troubleshooting

### Database Issues
```bash
# Port 5432 in use
docker compose down --remove-orphans
lsof -ti:5432 | xargs kill -9

# Reset test database
docker compose down --volumes
docker compose up -d --wait
```

### JWT Issues
- Generate new secret: `openssl rand -hex 32`
- Check token expiration in JWT debugger
- Verify `PyJWT` library (not `python-jose`)

### Import Issues
- Use absolute imports: `from src.models import User`
- Check ruff INP001 errors (missing `__init__.py`)

### Type Issues
- Use `datetime.now(timezone.utc)` not `datetime.utcnow()`
- UUID path params: `product_id: uuid.UUID`
- Pydantic V2: `model_config = ConfigDict(...)`

## Performance Notes

- **Search**: Uses PostgreSQL TSVECTOR with GIN index
- **Stock transfers**: Atomic with `SELECT FOR UPDATE`
- **Pagination**: Max 100 items per page
- **Rate limiting**: Per-endpoint limits via slowapi
- **Docker image**: <200MB production build

## Security

- **Passwords**: bcrypt hashed with salt rounds
- **JWT**: Access + refresh token pattern
- **API keys**: SHA-256 hashed storage
- **SQL injection**: Parameterized queries via SQLAlchemy
- **CORS**: Configured for frontend origin