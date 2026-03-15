"""Products API endpoints."""

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.dependencies import get_current_admin, get_current_user, get_db
from src.models import Category, Product
from src.schemas import PaginatedResponse, ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    search: str | None = Query(None, description="Full-text search query"),
    category_id: uuid.UUID | None = Query(None, description="Filter by category"),
    min_price: float | None = Query(None, ge=0, description="Minimum price filter"),
    max_price: float | None = Query(None, ge=0, description="Maximum price filter"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    sort_by: str | None = Query(None, description="Sort by field (name, price, created_at)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """List products with filters, search, and pagination."""
    offset = (page - 1) * per_page

    # Build base query
    query = select(Product)

    # Add filters
    filters = []

    if category_id:
        filters.append(Product.category_id == category_id)

    if min_price is not None:
        filters.append(Product.price >= Decimal(str(min_price)))

    if max_price is not None:
        filters.append(Product.price <= Decimal(str(max_price)))

    if is_active is not None:
        filters.append(Product.is_active == is_active)

    if filters:
        query = query.where(and_(*filters))

    # Full-text search
    if search:
        # Use PostgreSQL full-text search with ts_rank for relevance
        search_query = query.where(
            func.to_tsvector("english", Product.name + " " + func.coalesce(Product.description, "")).op("@@")(
                func.plainto_tsquery("english", search)
            )
        ).order_by(
            func.ts_rank(
                func.to_tsvector("english", Product.name + " " + func.coalesce(Product.description, "")),
                func.plainto_tsquery("english", search),
            ).desc()
        )
    else:
        search_query = query

    # Apply sorting if no search (search has its own ordering by relevance)
    if not search:
        if sort_by == "name":
            search_query = search_query.order_by(Product.name)
        elif sort_by == "price":
            search_query = search_query.order_by(Product.price)
        elif sort_by == "created_at":
            search_query = search_query.order_by(Product.created_at.desc())
        else:
            # Default sort by name
            search_query = search_query.order_by(Product.name)

    # Get total count for the same filters
    count_query = select(func.count(Product.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    if search:
        count_query = count_query.where(
            func.to_tsvector("english", Product.name + " " + func.coalesce(Product.description, "")).op("@@")(
                func.plainto_tsquery("english", search)
            )
        )

    total_result = db.execute(count_query)
    total = total_result.scalar()

    # Get products for current page
    products_result = db.execute(search_query.offset(offset).limit(per_page))
    products = products_result.scalars().all()

    return {
        "items": products,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> Product:
    """Create a new product (admin only)."""
    # Validate category exists
    category_result = db.execute(select(Category).where(Category.id == product_data.category_id))
    category = category_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")

    # Create product
    product = Product(
        name=product_data.name,
        sku=product_data.sku,
        description=product_data.description,
        price=Decimal(str(product_data.price)),
        category_id=product_data.category_id,
    )

    db.add(product)
    try:
        db.flush()  # Get the product.id

        # Update search vector using explicit UPDATE statement
        db.execute(
            update(Product)
            .where(Product.id == product.id)
            .values(
                search_vector=func.to_tsvector("english", Product.name + " " + func.coalesce(Product.description, ""))
            )
        )

        db.commit()
        db.refresh(product)
        return product
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product with this SKU already exists") from e


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> Product:
    """Get a product by ID with eager-loaded stock levels."""
    product_result = db.execute(
        select(Product).options(selectinload(Product.stock_levels)).where(Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: uuid.UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> Product:
    """Update a product (admin only)."""
    # Get existing product
    product_result = db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate category exists if provided
    if product_data.category_id:
        category_result = db.execute(select(Category).where(Category.id == product_data.category_id))
        category = category_result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")

    # Track if we need to update search vector
    update_search = False

    # Update fields
    if product_data.name is not None:
        product.name = product_data.name
        update_search = True
    if product_data.sku is not None:
        product.sku = product_data.sku
    if product_data.description is not None:
        product.description = product_data.description
        update_search = True
    if product_data.price is not None:
        product.price = Decimal(str(product_data.price))
    if product_data.category_id is not None:
        product.category_id = product_data.category_id
    if product_data.is_active is not None:
        product.is_active = product_data.is_active

    try:
        db.flush()

        # Update search vector if name or description changed
        if update_search:
            db.execute(
                update(Product)
                .where(Product.id == product.id)
                .values(
                    search_vector=func.to_tsvector(
                        "english", Product.name + " " + func.coalesce(Product.description, "")
                    )
                )
            )

        db.commit()
        db.refresh(product)
        return product
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product with this SKU already exists") from e


@router.delete("/{product_id}", response_model=ProductResponse)
def delete_product(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> Product:
    """Soft-delete a product (set is_active=false) (admin only)."""
    # Get product
    product_result = db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Soft-delete by setting is_active to False
    product.is_active = False

    db.commit()
    db.refresh(product)

    return product
