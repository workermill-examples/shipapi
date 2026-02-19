from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import api_router
from src.database import engine

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
