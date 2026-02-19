"""Audit recording service: persists audit log entries for all write operations."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog


async def record_audit(
    db: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Create and flush an :class:`AuditLog` entry without committing.

    The caller is responsible for committing (or rolling back) the surrounding
    transaction.  Using :meth:`~sqlalchemy.ext.asyncio.AsyncSession.flush` means
    the row is visible within the current transaction and gets the PK assigned,
    but the commit happens once, atomically, alongside the business-data change.

    Args:
        db: Active async database session.
        user_id: ID of the user performing the action.
        action: Short verb describing the operation, e.g. ``"create"``, ``"update"``,
            ``"delete"``.  Stored as-is; callers should use consistent strings.
        resource_type: Name of the affected resource, e.g. ``"category"``,
            ``"product"``.
        resource_id: Primary key of the affected row.
        changes: Optional mapping of changed fields.  For create operations pass
            the full new state; for updates pass only the changed fields as
            ``{field: {"old": old_value, "new": new_value}}``.
        ip_address: Optional client IP address for the request.

    Returns:
        The newly created :class:`AuditLog` instance (already flushed).
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry
