"""Common schemas used across multiple modules."""

from typing import TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponse[T](BaseModel):
    """Standard pagination wrapper for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    per_page: int
