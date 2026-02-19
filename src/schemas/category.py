"""Pydantic schemas for Category resources."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

_EXAMPLE_CATEGORY_ID = "7f3e1b2a-8c4d-4e5f-9a6b-1c2d3e4f5a6b"
_EXAMPLE_SUBCATEGORY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_EXAMPLE_PRODUCT_ID = "2a3b4c5d-6e7f-8a9b-0c1d-2e3f4a5b6c7d"
_EXAMPLE_TS = "2026-01-15T10:30:00Z"


class CategoryCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Electronics",
                "description": "Consumer electronics and accessories",
                "parent_id": None,
            }
        }
    )

    name: str = Field(..., max_length=100)
    description: str | None = None
    parent_id: uuid.UUID | None = None


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Consumer Electronics",
                "description": "Updated: now includes wearables and smart home devices",
            }
        }
    )

    name: str | None = Field(None, max_length=100)
    description: str | None = None
    parent_id: uuid.UUID | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_CATEGORY_ID,
                "name": "Electronics",
                "description": "Consumer electronics and accessories",
                "parent_id": None,
                "created_at": _EXAMPLE_TS,
                "updated_at": _EXAMPLE_TS,
            }
        },
    )

    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CategoryProductItem(BaseModel):
    """Simplified product representation for embedding in category detail."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_PRODUCT_ID,
                "name": "ProMax Smartphone X12",
                "sku": "ELEC-MON-001",
                "price": "999.99",
                "is_active": True,
                "created_at": "2026-01-10T08:00:00Z",
            }
        },
    )

    id: uuid.UUID
    name: str
    sku: str
    price: Decimal
    is_active: bool
    created_at: datetime


class CategoryDetailResponse(CategoryResponse):
    """CategoryResponse extended with a list of associated products."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_CATEGORY_ID,
                "name": "Electronics",
                "description": "Consumer electronics and accessories",
                "parent_id": None,
                "created_at": _EXAMPLE_TS,
                "updated_at": _EXAMPLE_TS,
                "products": [
                    {
                        "id": _EXAMPLE_PRODUCT_ID,
                        "name": "ProMax Smartphone X12",
                        "sku": "ELEC-MON-001",
                        "price": "999.99",
                        "is_active": True,
                        "created_at": "2026-01-10T08:00:00Z",
                    }
                ],
            }
        },
    )

    products: list[CategoryProductItem] = []
