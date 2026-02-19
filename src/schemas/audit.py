"""Pydantic schemas for the audit log endpoint."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Response schema for a single audit log entry."""

    model_config = ConfigDict(from_attributes=True)

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
