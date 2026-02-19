import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Computed, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        Index("ix_products_search_vector", "search_vector", postgresql_using="gin"),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3), nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', name || ' ' || coalesce(description, ''))",
            persisted=True,
        ),
    )

    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="products",
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id!r} sku={self.sku!r}>"
