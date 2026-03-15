"""FastAPI application factory with middleware, CORS, and router configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.config import settings
from src.middleware import AccessLogMiddleware, RequestIdMiddleware
from src.routers import audit, auth, categories, health, products, showcase, stock, warehouses

# Rate limiter for global middleware
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns a configured FastAPI app with:
    - CORS middleware for frontend integration
    - Request ID and access logging middleware
    - Rate limiting middleware (slowapi)
    - Authentication and health routers
    - OpenAPI/Swagger documentation with organized tags
    """
    app = FastAPI(
        title="ShipAPI",
        description="Production-grade inventory management REST API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "Health",
                "description": "Service health and status endpoints",
            },
            {
                "name": "Authentication",
                "description": "User registration, login, and API key management",
            },
            {
                "name": "Categories",
                "description": "Product category management with hierarchy support",
            },
            {
                "name": "Products",
                "description": "Product inventory with search, filtering, and sorting",
            },
            {
                "name": "Warehouses",
                "description": "Warehouse and storage location management",
            },
            {
                "name": "Stock",
                "description": "Stock levels, adjustments, and transfers",
            },
            {
                "name": "Audit",
                "description": "Audit logging and activity tracking",
            },
            {
                "name": "Showcase",
                "description": "Public showcase statistics and metrics",
            },
        ],
    )

    # Configure CORS for frontend integration
    # Note: In production, these origins should be restricted to actual frontend domains
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React dev server
            "http://localhost:5173",  # Vite dev server
            "http://localhost:8000",  # FastAPI serving frontend
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    # Add custom middleware using FastAPI's middleware system
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # Include routers with API v1 prefix
    app.include_router(health.router)  # health router already has /api/v1 prefix
    app.include_router(auth.router)  # auth router already has /api/v1 prefix
    app.include_router(categories.router)  # categories router already has /api/v1 prefix
    app.include_router(products.router)  # products router already has /api/v1 prefix
    app.include_router(warehouses.router)  # warehouses router already has /api/v1 prefix
    app.include_router(stock.router)  # stock router already has /api/v1 prefix
    app.include_router(audit.router)  # audit router already has /api/v1 prefix

    # Showcase router (outside /api/v1 prefix)
    app.include_router(showcase.router)

    # Root endpoint for basic service info
    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        """Root endpoint returning basic service information."""
        return {
            "service": "ShipAPI",
            "version": "0.1.0",
            "description": "Production-grade inventory management REST API",
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health",
        }

    return app


# Create the app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
