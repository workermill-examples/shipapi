from typing import List

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Warehouse(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_warehouses_capacity_positive"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    stock_levels: Mapped[List["StockLevel"]] = relationship(
        "StockLevel",
        back_populates="warehouse",
    )

    def __repr__(self) -> str:
        return f"<Warehouse id={self.id!r} name={self.name!r}>"
