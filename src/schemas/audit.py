"""Pydantic schemas for the audit log endpoint."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

_EXAMPLE_AUDIT_ID = "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b"
_EXAMPLE_USER_ID = "12345678-1234-1234-1234-123456789012"
_EXAMPLE_WAREHOUSE_ID = "c9d8e7f6-a5b4-3c2d-1e0f-9a8b7c6d5e4f"
_EXAMPLE_TS = "2026-01-15T10:30:00Z"


class AuditLogResponse(BaseModel):
    """Response schema for a single audit log entry."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_AUDIT_ID,
                "user_id": _EXAMPLE_USER_ID,
                "action": "create",
                "resource_type": "warehouse",
                "resource_id": _EXAMPLE_WAREHOUSE_ID,
                "changes": {
                    "name": "East Coast Hub",
                    "location": "New York, NY",
                    "capacity": 10000,
                },
                "ip_address": "203.0.113.42",
                "created_at": _EXAMPLE_TS,
            }
        },
    )

    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    resource_type: str
    resource_id: uuid.UUID
    changes: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime


class AuditLogQuery(BaseModel):
    """Query parameters for filtering and paginating audit log entries."""

    page: int = 1
    per_page: int = 20
    start_date: datetime | None = None
    end_date: datetime | None = None
    action: str | None = None
    resource_type: str | None = None
    user_id: uuid.UUID | None = None
