"""Reusable async pagination utility for SQLAlchemy async sessions."""

import math
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.common import PaginatedResponse, Pagination

_MAX_PER_PAGE = 100


async def paginate[T: BaseModel](
    db: AsyncSession,
    query: Select[Any],
    page: int,
    per_page: int,
    schema: type[T],
) -> PaginatedResponse[T]:
    """Execute *query* with pagination and return a :class:`PaginatedResponse`.

    Args:
        db: Active async database session.
        query: A SQLAlchemy :func:`select` statement (without offset/limit applied).
        page: 1-based page number.  Values < 1 are clamped to 1.
        per_page: Number of items per page.  Clamped to [1, 100].
        schema: Pydantic model class used to validate each ORM row.

    Returns:
        A :class:`PaginatedResponse` containing the page's items and pagination metadata.
    """
    # Clamp inputs
    page = max(page, 1)
    per_page = max(1, min(per_page, _MAX_PER_PAGE))

    # Total count via a wrapping subquery so any ORDER BY in the original query
    # is preserved without breaking the COUNT.
    count_query = select(func.count()).select_from(query.subquery())
    total: int = (await db.execute(count_query)).scalar_one()

    # Fetch the requested page
    offset = (page - 1) * per_page
    rows_result = await db.execute(query.offset(offset).limit(per_page))
    rows = rows_result.scalars().all()

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedResponse(
        data=[schema.model_validate(row) for row in rows],
        pagination=Pagination(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )
