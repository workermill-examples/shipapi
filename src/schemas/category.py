"""Category-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    """Request schema for creating a new category."""

    name: str = Field(min_length=1, max_length=255, description="Category name")
    description: str | None = Field(default=None, description="Category description")
    parent_id: uuid.UUID | None = Field(default=None, description="Parent category ID for subcategories")


class CategoryUpdate(BaseModel):
    """Request schema for updating a category."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Category name")
    description: str | None = Field(default=None, description="Category description")
    parent_id: uuid.UUID | None = Field(default=None, description="Parent category ID for subcategories")


class CategoryResponse(BaseModel):
    """Response schema for category information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    parent_id: uuid.UUID | None
    product_count: int | None = Field(default=None, description="Number of products in this category")
    created_at: datetime
    updated_at: datetime
