"""Category CRUD endpoints with admin guards, cascade protection, and audit logging."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.dependencies import get_db, require_admin
from src.models import Category, Product, User
from src.schemas.category import (
    CategoryCreate,
    CategoryDetailResponse,
    CategoryResponse,
    CategoryUpdate,
)
from src.schemas.common import PaginatedResponse
from src.services.audit import record_audit
from src.utils.pagination import paginate

router = APIRouter(prefix="/categories", tags=["Categories"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Category not found",
)


def _serialize_value(value: Any) -> Any:
    """Convert a field value to a JSON-safe type for audit log storage."""
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


@router.get("", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    page: int = Query(1, ge=1),  # noqa: B008
    per_page: int = Query(20, ge=1, le=100),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PaginatedResponse[CategoryResponse]:
    """Return categories as a paginated flat list ordered by name.

    Parent–child hierarchy is expressed via the ``parent_id`` field on each item.
    """
    query = select(Category).order_by(Category.name)
    return await paginate(db, query, page, per_page, CategoryResponse)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(require_admin),  # noqa: B008
) -> CategoryResponse:
    """Create a new category.  Admin only.

    Returns 400 if ``parent_id`` references a non-existent category.
    """
    category = Category(
        name=body.name,
        description=body.description,
        parent_id=body.parent_id,
    )
    db.add(category)
    await db.flush()  # assign PK before audit record

    await record_audit(
        db,
        user_id=current_user.id,
        action="create",
        resource_type="category",
        resource_id=category.id,
        changes={
            "name": body.name,
            "description": body.description,
            "parent_id": str(body.parent_id) if body.parent_id else None,
        },
        ip_address=request.client.host if request.client else None,
    )

    try:
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parent_id: referenced category does not exist",
        ) from None

    return CategoryResponse.model_validate(category)


@router.get("/{category_id}", response_model=CategoryDetailResponse)
async def get_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CategoryDetailResponse:
    """Return a single category with its full list of associated products."""
    result = await db.execute(
        select(Category).where(Category.id == category_id).options(selectinload(Category.products))
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise _NOT_FOUND
    return CategoryDetailResponse.model_validate(category)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(require_admin),  # noqa: B008
) -> CategoryResponse:
    """Update a category.  Admin only.

    Only fields explicitly included in the request body are modified.
    The audit log records only fields whose values actually changed.
    Returns 400 if ``parent_id`` references a non-existent category.
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise _NOT_FOUND

    update_data = body.model_dump(exclude_unset=True)
    changes: dict[str, dict[str, Any]] = {}

    for field, new_value in update_data.items():
        old_value = getattr(category, field)
        if old_value != new_value:
            changes[field] = {
                "old": _serialize_value(old_value),
                "new": _serialize_value(new_value),
            }
            setattr(category, field, new_value)

    if changes:
        await record_audit(
            db,
            user_id=current_user.id,
            action="update",
            resource_type="category",
            resource_id=category_id,
            changes=changes,
            ip_address=request.client.host if request.client else None,
        )
        try:
            await db.commit()
            await db.refresh(category)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent_id: referenced category does not exist",
            ) from None

    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(require_admin),  # noqa: B008
) -> None:
    """Delete a category.  Admin only.

    Returns 400 (INVALID_OPERATION) if the category has any products assigned to it,
    active or inactive — products must be re-assigned or deleted first.
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise _NOT_FOUND

    # Cascade protection: block delete when products reference this category
    count_result = await db.execute(
        select(func.count()).select_from(Product).where(Product.category_id == category_id)
    )
    product_count: int = count_result.scalar_one()
    if product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category: it still has products assigned to it",
        )

    await record_audit(
        db,
        user_id=current_user.id,
        action="delete",
        resource_type="category",
        resource_id=category_id,
        changes={"name": category.name},
        ip_address=request.client.host if request.client else None,
    )
    await db.delete(category)
    await db.commit()
