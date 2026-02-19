from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sku: str


class WarehouseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    location: str


class StockUpdateRequest(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

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
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: int
    initiated_by: UUID
    notes: str | None
    created_at: datetime


class StockAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductSummary
    warehouse: WarehouseSummary
    quantity: int
    min_threshold: int
    deficit: int
