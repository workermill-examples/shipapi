"""Audit log API endpoints."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.dependencies import get_current_admin, get_db
from src.models import AuditLog
from src.schemas import AuditLogResponse, PaginatedResponse

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Log"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
def get_audit_log(
    page: int = 1,
    per_page: int = 50,
    user_id: uuid.UUID | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    start_date: datetime | None = Query(None, description="Filter from this date (inclusive)"),
    end_date: datetime | None = Query(None, description="Filter to this date (inclusive)"),
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> dict[str, Any]:
    """Get audit log entries with filters (admin only)."""
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Build query with filters
    query = select(AuditLog)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    # Get total count with same filters
    count_query = select(func.count(AuditLog.id))
    if user_id:
        count_query = count_query.where(AuditLog.user_id == user_id)
    if action:
        count_query = count_query.where(AuditLog.action == action)
    if resource_type:
        count_query = count_query.where(AuditLog.resource_type == resource_type)
    if start_date:
        count_query = count_query.where(AuditLog.created_at >= start_date)
    if end_date:
        count_query = count_query.where(AuditLog.created_at <= end_date)

    total_result = db.execute(count_query)
    total = total_result.scalar()

    # Get audit entries for current page (newest first)
    audit_result = db.execute(
        query.order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page)
    )
    audit_entries = audit_result.scalars().all()

    return {
        "items": audit_entries,
        "total": total,
        "page": page,
        "per_page": per_page,
    }