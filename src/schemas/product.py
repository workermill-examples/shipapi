"""Pydantic schemas for Product resources."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas.category import CategoryResponse

_EXAMPLE_PRODUCT_ID = "2a3b4c5d-6e7f-8a9b-0c1d-2e3f4a5b6c7d"
_EXAMPLE_CATEGORY_ID = "7f3e1b2a-8c4d-4e5f-9a6b-1c2d3e4f5a6b"
_EXAMPLE_WAREHOUSE_ID = "c9d8e7f6-a5b4-3c2d-1e0f-9a8b7c6d5e4f"
_EXAMPLE_TS = "2026-01-10T08:00:00Z"
_EXAMPLE_CATEGORY: dict[str, Any] = {
    "id": _EXAMPLE_CATEGORY_ID,
    "name": "Electronics",
    "description": "Consumer electronics and accessories",
    "parent_id": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


class ProductCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "ProMax Smartphone X12",
                "sku": "ELEC-MON-001",
                "description": (
                    "A flagship smartphone featuring a 6.7-inch AMOLED display and 108MP camera. "
                    "Built for professionals who need performance on the go. "
                    "Includes organic glass back and 5G connectivity."
                ),
                "price": "999.99",
                "weight_kg": "0.185",
                "category_id": _EXAMPLE_CATEGORY_ID,
                "is_active": True,
            }
        }
    )

    name: str = Field(..., max_length=200)
    sku: str = Field(..., max_length=50)
    description: str | None = None
    price: Decimal = Field(..., ge=0, decimal_places=2)
    weight_kg: Decimal | None = Field(None, ge=0, decimal_places=3)
    category_id: uuid.UUID
    is_active: bool = True


class ProductUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price": "899.99",
                "description": (
                    "Updated: now includes wireless charging pad and extended warranty. "
                    "Ideal for running shoes enthusiasts who also need a powerful device."
                ),
            }
        }
    )

    name: str | None = Field(None, max_length=200)
    sku: str | None = Field(None, max_length=50)
    description: str | None = None
    price: Decimal | None = Field(None, ge=0, decimal_places=2)
    weight_kg: Decimal | None = Field(None, ge=0, decimal_places=3)
    category_id: uuid.UUID | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_PRODUCT_ID,
                "name": "ProMax Smartphone X12",
                "sku": "ELEC-MON-001",
                "description": (
                    "A flagship smartphone featuring a 6.7-inch AMOLED display and 108MP camera."
                ),
                "price": "999.99",
                "weight_kg": "0.185",
                "category_id": _EXAMPLE_CATEGORY_ID,
                "is_active": True,
                "created_at": _EXAMPLE_TS,
                "updated_at": _EXAMPLE_TS,
                "category": _EXAMPLE_CATEGORY,
            }
        },
    )

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

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_WAREHOUSE_ID,
                "name": "East Coast Hub",
                "location": "New York, NY",
            }
        },
    )

    id: uuid.UUID
    name: str
    location: str


class ProductStockLevel(BaseModel):
    """Stock level entry with warehouse info for product detail response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "warehouse_id": _EXAMPLE_WAREHOUSE_ID,
                "quantity": 142,
                "min_threshold": 20,
                "warehouse": {
                    "id": _EXAMPLE_WAREHOUSE_ID,
                    "name": "East Coast Hub",
                    "location": "New York, NY",
                },
            }
        },
    )

    warehouse_id: uuid.UUID
    quantity: int
    min_threshold: int
    warehouse: WarehouseStockInfo


class ProductDetailResponse(ProductResponse):
    """ProductResponse extended with per-warehouse stock levels."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_PRODUCT_ID,
                "name": "ProMax Smartphone X12",
                "sku": "ELEC-MON-001",
                "description": (
                    "A flagship smartphone featuring a 6.7-inch AMOLED display and 108MP camera."
                ),
                "price": "999.99",
                "weight_kg": "0.185",
                "category_id": _EXAMPLE_CATEGORY_ID,
                "is_active": True,
                "created_at": _EXAMPLE_TS,
                "updated_at": _EXAMPLE_TS,
                "category": _EXAMPLE_CATEGORY,
                "stock_levels": [
                    {
                        "warehouse_id": _EXAMPLE_WAREHOUSE_ID,
                        "quantity": 142,
                        "min_threshold": 20,
                        "warehouse": {
                            "id": _EXAMPLE_WAREHOUSE_ID,
                            "name": "East Coast Hub",
                            "location": "New York, NY",
                        },
                    }
                ],
            }
        },
    )

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
