"""Health check endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.dependencies import get_db

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with database connectivity verification.

    Returns the service status and database connectivity status.
    Used by load balancers and monitoring systems.
    """
    try:
        # Test database connectivity
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as err:
        db_status = "disconnected"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connectivity check failed"
        ) from err

    return {"status": "healthy", "database": db_status, "version": "0.1.0"}
