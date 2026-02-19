"""Stock management service: stock levels, atomic transfers, alerts, and warehouse summaries."""

import uuid

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.audit_log import AuditLog
from src.models.product import Product
from src.models.stock_level import StockLevel
from src.models.stock_transfer import StockTransfer
from src.models.user import User
from src.models.warehouse import Warehouse
from src.schemas.stock import StockUpdateRequest, TransferRequest


def _stock_with_relations() -> Select[tuple[StockLevel]]:
    """Return a base select for StockLevel with product and warehouse eager-loaded."""
    return select(StockLevel).options(
        selectinload(StockLevel.product),
        selectinload(StockLevel.warehouse),
    )


async def get_stock_level(
    db: AsyncSession,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
) -> StockLevel | None:
    """Return the stock level for a product in a warehouse, eagerly loading relations."""
    result = await db.execute(
        _stock_with_relations().where(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
        )
    )
    return result.scalar_one_or_none()


async def list_warehouse_stock(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
    page: int = 1,
    size: int = 20,
) -> tuple[list[StockLevel], int]:
    """Return paginated stock levels for a warehouse, ordered by creation date (newest first)."""
    count_result = await db.execute(
        select(func.count()).select_from(StockLevel).where(StockLevel.warehouse_id == warehouse_id)
    )
    total: int = count_result.scalar_one()

    offset = (page - 1) * size
    items_result = await db.execute(
        _stock_with_relations()
        .where(StockLevel.warehouse_id == warehouse_id)
        .order_by(StockLevel.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    return list(items_result.scalars().all()), total


async def upsert_stock_level(
    db: AsyncSession,
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    request: StockUpdateRequest,
    current_user: User,
    ip_address: str | None = None,
) -> StockLevel:
    """Create or update a stock level record, writing an audit log entry.

    Creates a new record if none exists for the (product, warehouse) pair.
    Updates quantity and optionally min_threshold on an existing record.
    Raises HTTP 404 if product or warehouse is not found.
    Raises HTTP 400 if warehouse is inactive.
    """
    # Verify product exists
    product_result = await db.execute(select(Product).where(Product.id == product_id))
    if product_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verify warehouse exists and is active
    warehouse_result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = warehouse_result.scalar_one_or_none()
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    if not warehouse.is_active:
        raise HTTPException(status_code=400, detail="Warehouse is not active")

    # Find existing stock level
    existing_result = await db.execute(
        select(StockLevel).where(
            StockLevel.product_id == product_id,
            StockLevel.warehouse_id == warehouse_id,
        )
    )
    stock_level = existing_result.scalar_one_or_none()

    if stock_level is None:
        action = "create"
        stock_level = StockLevel(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity=request.quantity,
            min_threshold=request.min_threshold if request.min_threshold is not None else 10,
        )
        db.add(stock_level)
    else:
        action = "update"
        stock_level.quantity = request.quantity
        if request.min_threshold is not None:
            stock_level.min_threshold = request.min_threshold

    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action=action,
        resource_type="stock_level",
        resource_id=stock_level.id,
        changes={
            "quantity": request.quantity,
            "min_threshold": stock_level.min_threshold,
        },
        ip_address=ip_address,
    )
    db.add(audit)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Stock level conflict, please retry") from None

    # Re-fetch with eager loads for response serialization
    refreshed_result = await db.execute(
        _stock_with_relations().where(StockLevel.id == stock_level.id)
    )
    return refreshed_result.scalar_one()


async def transfer_stock(
    db: AsyncSession,
    request: TransferRequest,
    current_user: User,
    ip_address: str | None = None,
) -> StockTransfer:
    """Atomically transfer stock from one warehouse to another.

    Uses SELECT FOR UPDATE on the source stock level to prevent race conditions.
    All mutations occur in a single transaction that rolls back on any failure.

    Raises HTTP 404 if product or either warehouse is not found / inactive.
    Raises HTTP 400 with detail "INSUFFICIENT_STOCK" if source quantity is too low.
    """
    # TransferRequest validators already ensure from != to and quantity > 0

    # Verify product exists
    product_result = await db.execute(select(Product).where(Product.id == request.product_id))
    if product_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verify source warehouse exists and is active
    from_warehouse_result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == request.from_warehouse_id,
            Warehouse.is_active.is_(True),
        )
    )
    if from_warehouse_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source warehouse not found or inactive")

    # Verify destination warehouse exists and is active
    to_warehouse_result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == request.to_warehouse_id,
            Warehouse.is_active.is_(True),
        )
    )
    if to_warehouse_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Destination warehouse not found or inactive")

    # SELECT FOR UPDATE on source to prevent concurrent over-deduction
    from_stock_result = await db.execute(
        select(StockLevel)
        .where(
            StockLevel.product_id == request.product_id,
            StockLevel.warehouse_id == request.from_warehouse_id,
        )
        .with_for_update()
    )
    from_stock = from_stock_result.scalar_one_or_none()

    if from_stock is None or from_stock.quantity < request.quantity:
        raise HTTPException(status_code=400, detail="INSUFFICIENT_STOCK")

    # Deduct from source
    from_stock.quantity -= request.quantity

    # Lock destination row as well (or create new record)
    to_stock_result = await db.execute(
        select(StockLevel)
        .where(
            StockLevel.product_id == request.product_id,
            StockLevel.warehouse_id == request.to_warehouse_id,
        )
        .with_for_update()
    )
    to_stock = to_stock_result.scalar_one_or_none()

    if to_stock is None:
        to_stock = StockLevel(
            product_id=request.product_id,
            warehouse_id=request.to_warehouse_id,
            quantity=request.quantity,
        )
        db.add(to_stock)
    else:
        to_stock.quantity += request.quantity

    # Create transfer record
    transfer = StockTransfer(
        product_id=request.product_id,
        from_warehouse_id=request.from_warehouse_id,
        to_warehouse_id=request.to_warehouse_id,
        quantity=request.quantity,
        initiated_by=current_user.id,
        notes=request.notes,
    )
    db.add(transfer)

    # Flush to obtain IDs before writing audit log
    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="transfer",
        resource_type="stock_level",
        resource_id=transfer.id,
        changes={
            "product_id": str(request.product_id),
            "from_warehouse_id": str(request.from_warehouse_id),
            "to_warehouse_id": str(request.to_warehouse_id),
            "quantity": request.quantity,
        },
        ip_address=ip_address,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(transfer)
    return transfer


async def get_stock_alerts(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> tuple[list[StockLevel], int]:
    """Return stock levels where quantity < min_threshold, sorted by deficit (desc).

    The caller is responsible for computing deficit = min_threshold - quantity per item.
    Returns (items, total) where items have product and warehouse eagerly loaded.
    """
    below_threshold = StockLevel.quantity < StockLevel.min_threshold
    deficit_expr = StockLevel.min_threshold - StockLevel.quantity

    count_result = await db.execute(
        select(func.count()).select_from(StockLevel).where(below_threshold)
    )
    total: int = count_result.scalar_one()

    offset = (page - 1) * size
    items_result = await db.execute(
        _stock_with_relations()
        .where(below_threshold)
        .order_by(deficit_expr.desc())
        .offset(offset)
        .limit(size)
    )
    return list(items_result.scalars().all()), total


async def get_warehouse_stock_summary(
    db: AsyncSession,
    warehouse_id: uuid.UUID,
) -> tuple[int, int, float]:
    """Return (total_products, total_quantity, capacity_utilization_pct) for a warehouse.

    total_products: count of distinct products with stock records in this warehouse.
    total_quantity: sum of all quantity values across products.
    capacity_utilization_pct: (total_quantity / capacity) * 100; 0.0 if capacity is 0.

    Raises HTTP 404 if the warehouse is not found.
    """
    warehouse_result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = warehouse_result.scalar_one_or_none()
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    agg_result = await db.execute(
        select(
            func.count(StockLevel.product_id.distinct()).label("total_products"),
            func.coalesce(func.sum(StockLevel.quantity), 0).label("total_quantity"),
        ).where(StockLevel.warehouse_id == warehouse_id)
    )
    row = agg_result.one()
    total_products: int = row.total_products
    total_quantity: int = row.total_quantity

    capacity_utilization_pct = (
        (total_quantity / warehouse.capacity * 100) if warehouse.capacity > 0 else 0.0
    )

    return total_products, total_quantity, capacity_utilization_pct
