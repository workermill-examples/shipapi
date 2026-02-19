"""Health check endpoint — always returns HTTP 200 for Railway healthchecks."""

from fastapi import APIRouter
from sqlalchemy import text

from src.config import settings
from src.database import AsyncSessionLocal
from src.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return application health.

    Executes ``SELECT 1`` to verify database connectivity.  Always returns
    HTTP 200 — Railway uses this endpoint as a liveness probe and will restart
    the container if it receives a non-200 response.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
        app_status = "ok"
    except Exception:
        db_status = "disconnected"
        app_status = "degraded"

    return HealthResponse(
        status=app_status,
        database=db_status,
        version=settings.version,
        built_by=settings.app_name,
    )
