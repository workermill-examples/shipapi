"""Product-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """Request schema for creating a new product."""

    name: str = Field(min_length=1, max_length=255, description="Product name")
    sku: str = Field(min_length=1, max_length=255, description="Stock Keeping Unit")
    description: str | None = Field(default=None, description="Product description")
    price: float = Field(gt=0, description="Product price")
    category_id: uuid.UUID = Field(description="Category ID")


class ProductUpdate(BaseModel):
    """Request schema for updating a product."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Product name")
    sku: str | None = Field(default=None, min_length=1, max_length=255, description="Stock Keeping Unit")
    description: str | None = Field(default=None, description="Product description")
    price: float | None = Field(default=None, gt=0, description="Product price")
    category_id: uuid.UUID | None = Field(default=None, description="Category ID")
    is_active: bool | None = Field(default=None, description="Active status")


class ProductResponse(BaseModel):
    """Response schema for product information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sku: str
    description: str | None
    price: float
    is_active: bool
    category_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProductListParams(BaseModel):
    """Request schema for product list query parameters."""

    search: str | None = Field(default=None, description="Full-text search query")
    category_id: uuid.UUID | None = Field(default=None, description="Filter by category")
    min_price: float | None = Field(default=None, ge=0, description="Minimum price filter")
    max_price: float | None = Field(default=None, ge=0, description="Maximum price filter")
    is_active: bool | None = Field(default=None, description="Filter by active status")
    sort_by: str | None = Field(default=None, description="Sort by field")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=50, ge=1, le=100, description="Items per page")
