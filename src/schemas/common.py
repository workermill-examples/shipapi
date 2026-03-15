"""Common schemas used across multiple modules."""

from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination wrapper for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    per_page: int