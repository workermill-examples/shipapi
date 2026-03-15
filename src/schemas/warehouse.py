"""Warehouse-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    """Request schema for creating a new warehouse."""

    name: str = Field(min_length=1, max_length=255, description="Warehouse name")
    code: str = Field(min_length=1, max_length=50, description="Warehouse code")
    address: str = Field(min_length=1, description="Warehouse address")


class WarehouseUpdate(BaseModel):
    """Request schema for updating a warehouse."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Warehouse name")
    code: str | None = Field(default=None, min_length=1, max_length=50, description="Warehouse code")
    address: str | None = Field(default=None, min_length=1, description="Warehouse address")
    is_active: bool | None = Field(default=None, description="Active status")


class StockSummary(BaseModel):
    """Stock summary for warehouse detail response."""

    total_items: int = Field(description="Total number of items")
    total_quantity: int = Field(description="Total stock quantity across all products")


class WarehouseResponse(BaseModel):
    """Response schema for warehouse information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    address: str
    is_active: bool
    stock_summary: StockSummary | None = Field(default=None, description="Stock summary (only in detail endpoint)")
    created_at: datetime
    updated_at: datetime
