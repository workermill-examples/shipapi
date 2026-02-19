"""Pydantic schemas for Category resources."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    parent_id: uuid.UUID | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    parent_id: uuid.UUID | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    parent_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CategoryProductItem(BaseModel):
    """Simplified product representation for embedding in category detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sku: str
    price: Decimal
    is_active: bool
    created_at: datetime


class CategoryDetailResponse(CategoryResponse):
    """CategoryResponse extended with a list of associated products."""

    products: list[CategoryProductItem] = []
