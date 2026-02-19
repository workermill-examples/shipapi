from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

_EXAMPLE_WAREHOUSE_ID = "c9d8e7f6-a5b4-3c2d-1e0f-9a8b7c6d5e4f"
_EXAMPLE_TS = "2026-01-01T08:00:00Z"


class WarehouseCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "East Coast Hub",
                "location": "New York, NY",
                "capacity": 10000,
            }
        }
    )

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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "capacity": 12000,
                "is_active": True,
            }
        }
    )

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
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_WAREHOUSE_ID,
                "name": "East Coast Hub",
                "location": "New York, NY",
                "capacity": 10000,
                "is_active": True,
                "created_at": _EXAMPLE_TS,
                "updated_at": _EXAMPLE_TS,
            }
        },
    )

    id: UUID
    name: str
    location: str
    capacity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WarehouseDetailResponse(WarehouseResponse):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_WAREHOUSE_ID,
                "name": "East Coast Hub",
                "location": "New York, NY",
                "capacity": 10000,
                "is_active": True,
                "created_at": _EXAMPLE_TS,
                "updated_at": _EXAMPLE_TS,
                "total_products": 38,
                "total_quantity": 1542,
                "capacity_utilization_pct": 15.42,
            }
        },
    )

    total_products: int
    total_quantity: int
    capacity_utilization_pct: float
