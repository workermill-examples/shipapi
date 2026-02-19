"""Product CRUD endpoints with full-text search, combined filters, and audit logging."""

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.dependencies import get_current_user, get_db, require_admin
from src.models import Product, StockLevel, User
from src.schemas.category import CategoryResponse
from src.schemas.common import PaginatedResponse
from src.schemas.product import (
    ProductCreate,
    ProductDetailResponse,
    ProductListParams,
    ProductResponse,
    ProductStockLevel,
    ProductUpdate,
    SortOrder,
)
from src.services.audit import record_audit
from src.utils.pagination import paginate

router = APIRouter(prefix="/products", tags=["Products"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Product not found",
)


def _serialize_value(value: Any) -> Any:
    """Convert a field value to a JSON-safe type for audit log storage."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    params: ProductListParams = Depends(),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PaginatedResponse[ProductResponse]:
    """Return products as a paginated, filterable, searchable list.

    When ``search`` is provided, results are ranked by full-text relevance using
    ``ts_rank``.  Otherwise, results are sorted by ``sort_by`` / ``sort_order``.
    All filters (``category_id``, ``min_price``, ``max_price``, ``is_active``) are
    optional and combinable.
    """
    query = select(Product).options(selectinload(Product.category))

    # Full-text search — order by relevance when a search term is active
    if params.search:
        tsquery = func.plainto_tsquery("english", params.search)
        query = query.where(Product.search_vector.op("@@")(tsquery))
        query = query.order_by(func.ts_rank(Product.search_vector, tsquery).desc())
    else:
        sort_col = getattr(Product, params.sort_by)
        if params.sort_order == SortOrder.asc:
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

    # Optional filters
    if params.category_id is not None:
        query = query.where(Product.category_id == params.category_id)
    if params.min_price is not None:
        query = query.where(Product.price >= params.min_price)
    if params.max_price is not None:
        query = query.where(Product.price <= params.max_price)
    if params.is_active is not None:
        query = query.where(Product.is_active == params.is_active)

    return await paginate(db, query, params.page, params.per_page, ProductResponse)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ProductResponse:
    """Create a new product.  Requires authentication.

    Returns 400 if ``category_id`` references a non-existent category.
    Returns 409 if the SKU is already in use.
    """
    product = Product(
        name=body.name,
        sku=body.sku,
        description=body.description,
        price=body.price,
        weight_kg=body.weight_kg,
        category_id=body.category_id,
        is_active=body.is_active,
    )
    db.add(product)
    await db.flush()  # assign PK before audit record

    await record_audit(
        db,
        user_id=current_user.id,
        action="create",
        resource_type="product",
        resource_id=product.id,
        changes={
            "name": body.name,
            "sku": body.sku,
            "description": body.description,
            "price": str(body.price),
            "weight_kg": str(body.weight_kg) if body.weight_kg is not None else None,
            "category_id": str(body.category_id),
            "is_active": body.is_active,
        },
        ip_address=request.client.host if request.client else None,
    )

    try:
        await db.commit()
        await db.refresh(product)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category_id: referenced category does not exist",
        ) from None

    # Reload with category relationship for the response schema
    result = await db.execute(
        select(Product).where(Product.id == product.id).options(selectinload(Product.category))
    )
    return ProductResponse.model_validate(result.scalar_one())


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ProductDetailResponse:
    """Return a single product with full details including per-warehouse stock levels."""
    result = await db.execute(
        select(Product).where(Product.id == product_id).options(selectinload(Product.category))
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise _NOT_FOUND

    # Load stock levels with warehouse info (no ORM back-reference on Product)
    sl_result = await db.execute(
        select(StockLevel)
        .where(StockLevel.product_id == product_id)
        .options(selectinload(StockLevel.warehouse))
    )
    stock_levels = sl_result.scalars().all()

    return ProductDetailResponse(
        id=product.id,
        name=product.name,
        sku=product.sku,
        description=product.description,
        price=product.price,
        weight_kg=product.weight_kg,
        category_id=product.category_id,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        category=CategoryResponse.model_validate(product.category),
        stock_levels=[ProductStockLevel.model_validate(sl) for sl in stock_levels],
    )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ProductResponse:
    """Update a product.  Requires authentication.

    Only fields explicitly included in the request body are modified.
    The audit log records only fields whose values actually changed.
    Returns 400 if ``category_id`` references a non-existent category or SKU is
    already in use.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise _NOT_FOUND

    update_data = body.model_dump(exclude_unset=True)
    changes: dict[str, dict[str, Any]] = {}

    for field, new_value in update_data.items():
        old_value = getattr(product, field)
        if old_value != new_value:
            changes[field] = {
                "old": _serialize_value(old_value),
                "new": _serialize_value(new_value),
            }
            setattr(product, field, new_value)

    if changes:
        await record_audit(
            db,
            user_id=current_user.id,
            action="update",
            resource_type="product",
            resource_id=product_id,
            changes=changes,
            ip_address=request.client.host if request.client else None,
        )
        try:
            await db.commit()
            await db.refresh(product)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category_id or SKU already in use",
            ) from None

    # Reload with category relationship for the response schema
    result = await db.execute(
        select(Product).where(Product.id == product_id).options(selectinload(Product.category))
    )
    return ProductResponse.model_validate(result.scalar_one())


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    current_user: User = Depends(require_admin),  # noqa: B008
) -> None:
    """Soft-delete a product.  Admin only.

    Sets ``is_active=False`` rather than deleting the row so that FK references
    from stock levels, transfers, and audit logs remain intact.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if product is None:
        raise _NOT_FOUND

    product.is_active = False

    await record_audit(
        db,
        user_id=current_user.id,
        action="delete",
        resource_type="product",
        resource_id=product_id,
        changes={"name": product.name, "sku": product.sku},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
