"""Pydantic schemas for Product resources."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas.category import CategoryResponse


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    sku: str = Field(..., max_length=50)
    description: str | None = None
    price: Decimal = Field(..., ge=0, decimal_places=2)
    weight_kg: Decimal | None = Field(None, ge=0, decimal_places=3)
    category_id: uuid.UUID
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    sku: str | None = Field(None, max_length=50)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0, decimal_places=2)
    weight_kg: Decimal | None = Field(None, ge=0, decimal_places=3)
    category_id: uuid.UUID | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sku: str
    description: str | None
    price: Decimal
    weight_kg: Decimal | None
    category_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse


class WarehouseStockInfo(BaseModel):
    """Warehouse info embedded in stock level response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    location: str


class ProductStockLevel(BaseModel):
    """Stock level entry with warehouse info for product detail response."""

    model_config = ConfigDict(from_attributes=True)

    warehouse_id: uuid.UUID
    quantity: int
    min_threshold: int
    warehouse: WarehouseStockInfo


class ProductDetailResponse(ProductResponse):
    """ProductResponse extended with per-warehouse stock levels."""

    stock_levels: list[ProductStockLevel] = []


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


# Allowed sort column names (whitelist to prevent SQL injection via column name)
ProductSortField = Literal["name", "price", "created_at", "sku"]


class ProductListParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1)
    sort_by: ProductSortField = "created_at"
    sort_order: SortOrder = SortOrder.desc
    search: str | None = None
    category_id: uuid.UUID | None = None
    min_price: Decimal | None = Field(None, ge=0)
    max_price: Decimal | None = Field(None, ge=0)
    is_active: bool | None = None

    @field_validator("per_page", mode="before")
    @classmethod
    def clamp_per_page(cls, v: int) -> int:
        """Silently clamp per_page to a maximum of 100 instead of raising a validation error."""
        return min(int(v), 100)
