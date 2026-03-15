"""Audit log Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Response schema for audit log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    action: str
    resource_type: str
    resource_id: uuid.UUID
    details: Optional[dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime
    updated_at: datetime