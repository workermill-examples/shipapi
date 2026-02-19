import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.product import Product
    from src.models.user import User
    from src.models.warehouse import Warehouse


class StockTransfer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "stock_transfers"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_stock_transfers_quantity_positive"),
        CheckConstraint(
            "from_warehouse_id != to_warehouse_id",
            name="ck_stock_transfers_different_warehouses",
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )
    from_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
    )
    to_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship("Product")
    from_warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        foreign_keys=[from_warehouse_id],
    )
    to_warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        foreign_keys=[to_warehouse_id],
    )
    initiator: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<StockTransfer id={self.id!r} product_id={self.product_id!r} "
            f"quantity={self.quantity!r}>"
        )
