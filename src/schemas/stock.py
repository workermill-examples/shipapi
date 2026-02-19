from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_EXAMPLE_PRODUCT_ID = "2a3b4c5d-6e7f-8a9b-0c1d-2e3f4a5b6c7d"
_EXAMPLE_WAREHOUSE_ID_1 = "c9d8e7f6-a5b4-3c2d-1e0f-9a8b7c6d5e4f"
_EXAMPLE_WAREHOUSE_ID_2 = "d8e7f6a5-b4c3-2d1e-0f9a-8b7c6d5e4f3c"
_EXAMPLE_STOCK_ID = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
_EXAMPLE_TRANSFER_ID = "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"
_EXAMPLE_USER_ID = "12345678-1234-1234-1234-123456789012"
_EXAMPLE_TS = "2026-01-15T10:30:00Z"


class ProductSummary(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_PRODUCT_ID,
                "name": "ProMax Smartphone X12",
                "sku": "ELEC-MON-001",
            }
        },
    )

    id: UUID
    name: str
    sku: str


class WarehouseSummary(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_WAREHOUSE_ID_1,
                "name": "East Coast Hub",
                "location": "New York, NY",
            }
        },
    )

    id: UUID
    name: str
    location: str


class StockUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quantity": 150,
                "min_threshold": 20,
            }
        }
    )

    quantity: int
    min_threshold: int | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity must be >= 0")
        return v

    @field_validator("min_threshold")
    @classmethod
    def threshold_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("min_threshold must be >= 0")
        return v


class StockLevelResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_STOCK_ID,
                "product_id": _EXAMPLE_PRODUCT_ID,
                "warehouse_id": _EXAMPLE_WAREHOUSE_ID_1,
                "product": {
                    "id": _EXAMPLE_PRODUCT_ID,
                    "name": "ProMax Smartphone X12",
                    "sku": "ELEC-MON-001",
                },
                "warehouse": {
                    "id": _EXAMPLE_WAREHOUSE_ID_1,
                    "name": "East Coast Hub",
                    "location": "New York, NY",
                },
                "quantity": 150,
                "min_threshold": 20,
                "created_at": _EXAMPLE_TS,
                "updated_at": _EXAMPLE_TS,
            }
        },
    )

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    product: ProductSummary
    warehouse: WarehouseSummary
    quantity: int
    min_threshold: int
    created_at: datetime
    updated_at: datetime


class TransferRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_id": _EXAMPLE_PRODUCT_ID,
                "from_warehouse_id": _EXAMPLE_WAREHOUSE_ID_1,
                "to_warehouse_id": _EXAMPLE_WAREHOUSE_ID_2,
                "quantity": 25,
                "notes": "Seasonal rebalancing — Q1 demand shift to West Coast.",
            }
        }
    )

    product_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: int
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Transfer quantity must be > 0")
        return v

    @model_validator(mode="after")
    def different_warehouses(self) -> "TransferRequest":
        if self.from_warehouse_id == self.to_warehouse_id:
            raise ValueError("from_warehouse_id and to_warehouse_id must be different")
        return self


class TransferResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": _EXAMPLE_TRANSFER_ID,
                "product_id": _EXAMPLE_PRODUCT_ID,
                "from_warehouse_id": _EXAMPLE_WAREHOUSE_ID_1,
                "to_warehouse_id": _EXAMPLE_WAREHOUSE_ID_2,
                "quantity": 25,
                "initiated_by": _EXAMPLE_USER_ID,
                "notes": "Seasonal rebalancing — Q1 demand shift to West Coast.",
                "created_at": _EXAMPLE_TS,
            }
        },
    )

    id: UUID
    product_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: int
    initiated_by: UUID
    notes: str | None
    created_at: datetime


class StockAlertResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "product": {
                    "id": _EXAMPLE_PRODUCT_ID,
                    "name": "ProMax Smartphone X12",
                    "sku": "ELEC-MON-001",
                },
                "warehouse": {
                    "id": _EXAMPLE_WAREHOUSE_ID_1,
                    "name": "East Coast Hub",
                    "location": "New York, NY",
                },
                "quantity": 3,
                "min_threshold": 20,
                "deficit": 17,
            }
        },
    )

    product: ProductSummary
    warehouse: WarehouseSummary
    quantity: int
    min_threshold: int
    deficit: int
