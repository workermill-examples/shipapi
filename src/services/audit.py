"""Audit recording service.

Provides two public async functions:
- ``record_audit_log`` — called from any write endpoint to persist an audit entry.
- ``list_audit_logs`` — paginated, filtered read used by the admin audit endpoint.
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog
from src.schemas.audit import AuditLogQuery


async def record_audit_log(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Create and persist an ``AuditLog`` record.

    Designed to be called explicitly from any write endpoint after the primary
    mutation has been committed.  Commits its own transaction and refreshes
    the returned instance.
    """
    audit = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=ip_address,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)
    return audit


#: Alias for ``record_audit_log`` — used by ``src/services/__init__.py`` and endpoint modules.
record_audit = record_audit_log


async def list_audit_logs(
    db: AsyncSession,
    query: AuditLogQuery,
) -> tuple[list[AuditLog], int]:
    """Return a paginated, filtered list of audit log entries and the total match count.

    Filters are applied as equality or range constraints based on the fields
    present in *query*.  Results are ordered newest-first by ``created_at``.
    Returns a ``(logs, total)`` tuple where ``total`` is the count before
    pagination so callers can compute ``total_pages``.
    """
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if query.start_date is not None:
        stmt = stmt.where(AuditLog.created_at >= query.start_date)
        count_stmt = count_stmt.where(AuditLog.created_at >= query.start_date)

    if query.end_date is not None:
        stmt = stmt.where(AuditLog.created_at <= query.end_date)
        count_stmt = count_stmt.where(AuditLog.created_at <= query.end_date)

    if query.action is not None:
        stmt = stmt.where(AuditLog.action == query.action)
        count_stmt = count_stmt.where(AuditLog.action == query.action)

    if query.resource_type is not None:
        stmt = stmt.where(AuditLog.resource_type == query.resource_type)
        count_stmt = count_stmt.where(AuditLog.resource_type == query.resource_type)

    if query.user_id is not None:
        stmt = stmt.where(AuditLog.user_id == query.user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == query.user_id)

    total_result = await db.execute(count_stmt)
    total: int = total_result.scalar_one()

    offset = (query.page - 1) * query.per_page
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(query.per_page)

    result = await db.execute(stmt)
    logs: list[AuditLog] = list(result.scalars().all())

    return logs, total
