from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class WarehouseCreate(BaseModel):
    name: str
    location: str
    capacity: int

    @field_validator("name", "location")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be empty")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Capacity must be greater than 0")
        return v


class WarehouseUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    capacity: int | None = None
    is_active: bool | None = None

    @field_validator("name", "location")
    @classmethod
    def strip_and_require(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Field must not be empty")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Capacity must be greater than 0")
        return v


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    location: str
    capacity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WarehouseDetailResponse(WarehouseResponse):
    total_products: int
    total_quantity: int
    capacity_utilization_pct: float
