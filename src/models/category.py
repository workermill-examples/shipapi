import uuid
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin


class Category(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="children",
        foreign_keys="[Category.parent_id]",
        remote_side="[Category.id]",
    )
    children: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
        foreign_keys="[Category.parent_id]",
    )
    products: Mapped[List["Product"]] = relationship(
        "Product",
        back_populates="category",
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id!r} name={self.name!r}>"
