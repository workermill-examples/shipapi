"""Stock-related Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StockLevelResponse(BaseModel):
    """Response schema for stock level information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    low_stock_threshold: int
    created_at: datetime
    updated_at: datetime


class StockAdjustRequest(BaseModel):
    """Request schema for stock adjustment (PUT /api/v1/stock/adjust)."""

    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(ge=0, description="New stock quantity")
    low_stock_threshold: int = Field(default=10, ge=0, description="Low stock alert threshold")


class StockTransferCreate(BaseModel):
    """Request schema for creating a stock transfer."""

    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: int = Field(gt=0, description="Quantity to transfer")
    notes: Optional[str] = Field(default=None, max_length=500, description="Transfer notes")


class StockTransferResponse(BaseModel):
    """Response schema for stock transfer information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime