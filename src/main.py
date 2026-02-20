from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from src.api.router import api_router
from src.api.showcase import root_router
from src.database import engine
from src.middleware.access_log import AccessLogMiddleware
from src.middleware.error_handler import (
    http_exception_handler,
    integrity_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from src.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from src.middleware.request_id import RequestIdMiddleware

_OPENAPI_TAGS = [
    {"name": "Health", "description": "Health check endpoints"},
    {"name": "Auth", "description": "Authentication and authorization"},
    {"name": "Categories", "description": "Product category management"},
    {"name": "Products", "description": "Product catalog management"},
    {"name": "Warehouses", "description": "Warehouse management"},
    {"name": "Stock", "description": "Stock level management"},
    {"name": "Audit", "description": "Audit log access"},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Startup: verify database connection
    async with engine.connect() as conn:
        await conn.run_sync(lambda _: None)
    yield
    # Shutdown: dispose all connections
    await engine.dispose()


app = FastAPI(
    title="ShipAPI",
    description="Inventory management REST API showcase",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=_OPENAPI_TAGS,
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

# ---------------------------------------------------------------------------
# Rate limiter — attach state and register 429 exception handler
# ---------------------------------------------------------------------------

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ---------------------------------------------------------------------------
# Middleware (Starlette LIFO: last add_middleware call runs outermost)
# ---------------------------------------------------------------------------

# CORSMiddleware runs innermost — registered first.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AccessLogMiddleware reads REQUEST_ID_CTX written by RequestIdMiddleware, so it
# must run inside it (closer to the application).
app.add_middleware(AccessLogMiddleware)

# RequestIdMiddleware runs outermost — registered last so it is the first layer
# to execute on every request and the last to complete on every response.
app.add_middleware(RequestIdMiddleware)

app.include_router(root_router)
app.include_router(api_router)
