import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import UUID, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.product import Product
    from src.models.warehouse import Warehouse


class StockLevel(Base):
    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_stock_level_product_warehouse"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stock_levels")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="stock_levels")


class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    from_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )
    to_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship("Product")
    from_warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[to_warehouse_id])