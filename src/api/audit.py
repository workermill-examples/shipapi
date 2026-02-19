"""Audit log endpoint — admin-only read access to the audit trail."""

import math
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, require_admin
from src.models import User
from src.schemas.audit import AuditLogQuery, AuditLogResponse
from src.schemas.common import PaginatedResponse, Pagination
from src.services.audit import list_audit_logs

router = APIRouter(tags=["Audit"])


@router.get("/audit-log", response_model=PaginatedResponse[AuditLogResponse])
async def get_audit_log(
    q: Annotated[AuditLogQuery, Depends()],
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[AuditLogResponse]:
    """Return a paginated, filterable view of the audit log.

    Restricted to admin users.  Supports filtering by date range, action,
    resource type, and the user who performed the action.
    """
    logs, total = await list_audit_logs(db, q)
    total_pages = math.ceil(total / q.per_page) if q.per_page > 0 else 0
    return PaginatedResponse[AuditLogResponse](
        data=[AuditLogResponse.model_validate(log) for log in logs],
        pagination=Pagination(
            page=q.page,
            per_page=q.per_page,
            total=total,
            total_pages=total_pages,
        ),
    )
