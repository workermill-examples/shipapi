import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class StockLevel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_stock_levels_product_warehouse"),
        CheckConstraint("quantity >= 0", name="ck_stock_levels_quantity_non_negative"),
        CheckConstraint("min_threshold >= 0", name="ck_stock_levels_min_threshold_non_negative"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="stock_levels",
    )

    def __repr__(self) -> str:
        return f"<StockLevel id={self.id!r} product_id={self.product_id!r} warehouse_id={self.warehouse_id!r}>"
