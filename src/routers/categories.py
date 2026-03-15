"""Categories API endpoints."""

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.dependencies import get_current_admin, get_current_user, get_db
from src.models import Category, Product
from src.schemas import CategoryCreate, CategoryResponse, CategoryUpdate, PaginatedResponse

router = APIRouter(prefix="/api/v1/categories", tags=["Categories"])


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a category name.

    Args:
        name: The category name

    Returns:
        A slug suitable for URLs
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@router.get("", response_model=PaginatedResponse[CategoryResponse])
def list_categories(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """List all categories with pagination."""
    per_page = min(per_page, 100)

    offset = (page - 1) * per_page

    # Get total count
    total_result = db.execute(select(func.count(Category.id)))
    total = total_result.scalar()

    # Get categories for current page
    categories_result = db.execute(select(Category).order_by(Category.name).offset(offset).limit(per_page))
    categories = categories_result.scalars().all()

    return {
        "items": categories,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> Category:
    """Create a new category (admin only)."""
    # Generate slug from name
    slug = generate_slug(category_data.name)

    # Validate parent exists if provided
    if category_data.parent_id:
        parent_result = db.execute(select(Category).where(Category.id == category_data.parent_id))
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent category not found")

    # Create category
    category = Category(
        name=category_data.name,
        slug=slug,
        description=category_data.description,
        parent_id=category_data.parent_id,
    )

    db.add(category)
    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Category with this slug already exists"
        ) from e


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> CategoryResponse:
    """Get a category by ID with product count."""
    # Get the category
    category_result = db.execute(select(Category).where(Category.id == category_id))
    category = category_result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Calculate product count
    product_count_result = db.execute(select(func.count(Product.id)).where(Product.category_id == category.id))
    product_count = product_count_result.scalar()

    # Convert to response model and add product count
    response_data = CategoryResponse.model_validate(category)
    response_data.product_count = product_count

    return response_data


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> Category:
    """Update a category (admin only)."""
    # Get existing category
    category_result = db.execute(select(Category).where(Category.id == category_id))
    category = category_result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Validate parent exists if provided
    if category_data.parent_id:
        # Can't set self as parent
        if category_data.parent_id == category_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category cannot be its own parent")

        parent_result = db.execute(select(Category).where(Category.id == category_data.parent_id))
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent category not found")

    # Update fields
    if category_data.name is not None:
        category.name = category_data.name
        category.slug = generate_slug(category_data.name)
    if category_data.description is not None:
        category.description = category_data.description
    if category_data.parent_id is not None:
        category.parent_id = category_data.parent_id

    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Category with this slug already exists"
        ) from e


@router.delete("/{category_id}")
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> dict[str, str]:
    """Delete a category (admin only). Cannot delete if it has products."""
    # Get category
    category_result = db.execute(select(Category).where(Category.id == category_id))
    category = category_result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Check if category has products
    product_count_result = db.execute(select(func.count(Product.id)).where(Product.category_id == category.id))
    product_count = product_count_result.scalar() or 0

    if product_count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete category with products")

    # Delete category
    db.delete(category)
    db.commit()

    return {"detail": "Category deleted successfully"}
