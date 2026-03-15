"""Stock management API endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.dependencies import get_current_admin, get_current_user, get_db
from src.models import Product, StockLevel, StockTransfer, Warehouse
from src.schemas import (
    PaginatedResponse,
    StockAdjustRequest,
    StockLevelResponse,
    StockTransferCreate,
    StockTransferResponse,
)

router = APIRouter(prefix="/api/v1/stock", tags=["Stock Management"])


@router.get("", response_model=PaginatedResponse[StockLevelResponse])
def list_stock_levels(
    page: int = 1,
    per_page: int = 50,
    warehouse_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """List stock levels with optional warehouse and product filters."""
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Build query with filters
    query = select(StockLevel)

    if warehouse_id:
        query = query.where(StockLevel.warehouse_id == warehouse_id)
    if product_id:
        query = query.where(StockLevel.product_id == product_id)

    # Get total count
    count_query = select(func.count(StockLevel.id))
    if warehouse_id:
        count_query = count_query.where(StockLevel.warehouse_id == warehouse_id)
    if product_id:
        count_query = count_query.where(StockLevel.product_id == product_id)

    total_result = db.execute(count_query)
    total = total_result.scalar()

    # Get stock levels for current page
    stock_levels_result = db.execute(query.order_by(StockLevel.created_at.desc()).offset(offset).limit(per_page))
    stock_levels = stock_levels_result.scalars().all()

    return {
        "items": stock_levels,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/alerts", response_model=PaginatedResponse[StockLevelResponse])
def get_low_stock_alerts(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get stock levels below their low stock threshold."""
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Query for low stock items (quantity < low_stock_threshold)
    query = select(StockLevel).where(StockLevel.quantity < StockLevel.low_stock_threshold)

    # Get total count
    total_result = db.execute(
        select(func.count(StockLevel.id)).where(StockLevel.quantity < StockLevel.low_stock_threshold)
    )
    total = total_result.scalar()

    # Get low stock items for current page
    stock_levels_result = db.execute(query.order_by(StockLevel.quantity.asc()).offset(offset).limit(per_page))
    stock_levels = stock_levels_result.scalars().all()

    return {
        "items": stock_levels,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.put("/adjust", response_model=StockLevelResponse)
def adjust_stock(
    stock_data: StockAdjustRequest,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> StockLevel:
    """Set stock level for a product+warehouse pair (admin only). Creates if not exists (upsert)."""
    # Validate product exists
    product_result = db.execute(select(Product).where(Product.id == stock_data.product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate warehouse exists
    warehouse_result = db.execute(select(Warehouse).where(Warehouse.id == stock_data.warehouse_id))
    warehouse = warehouse_result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    # Check if stock level already exists
    stock_level_result = db.execute(
        select(StockLevel).where(
            StockLevel.product_id == stock_data.product_id,
            StockLevel.warehouse_id == stock_data.warehouse_id,
        )
    )
    stock_level = stock_level_result.scalar_one_or_none()

    if stock_level:
        # Update existing stock level
        stock_level.quantity = stock_data.quantity
        stock_level.low_stock_threshold = stock_data.low_stock_threshold
    else:
        # Create new stock level
        stock_level = StockLevel(
            product_id=stock_data.product_id,
            warehouse_id=stock_data.warehouse_id,
            quantity=stock_data.quantity,
            low_stock_threshold=stock_data.low_stock_threshold,
        )
        db.add(stock_level)

    db.commit()
    db.refresh(stock_level)

    # TODO: Record audit log entry with old and new quantity
    # This would be implemented when the audit logging middleware is added

    return stock_level


@router.post("/transfers", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED)
def create_stock_transfer(
    transfer_data: StockTransferCreate,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> StockTransfer:
    """Create atomic stock transfer between warehouses."""
    # Validate different source and destination warehouses
    if transfer_data.from_warehouse_id == transfer_data.to_warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination warehouses must be different",
        )

    # Validate product exists
    product_result = db.execute(select(Product).where(Product.id == transfer_data.product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate warehouses exist
    from_warehouse_result = db.execute(select(Warehouse).where(Warehouse.id == transfer_data.from_warehouse_id))
    from_warehouse = from_warehouse_result.scalar_one_or_none()
    if not from_warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source warehouse not found")

    to_warehouse_result = db.execute(select(Warehouse).where(Warehouse.id == transfer_data.to_warehouse_id))
    to_warehouse = to_warehouse_result.scalar_one_or_none()
    if not to_warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination warehouse not found")

    # Use SELECT FOR UPDATE for atomic transfer within transaction
    try:
        # Get source stock level with lock
        source_stock_result = db.execute(
            select(StockLevel)
            .where(
                StockLevel.product_id == transfer_data.product_id,
                StockLevel.warehouse_id == transfer_data.from_warehouse_id,
            )
            .with_for_update()
        )
        source_stock = source_stock_result.scalar_one_or_none()

        if not source_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No stock available at source warehouse",
            )

        # Validate sufficient stock
        if source_stock.quantity < transfer_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {source_stock.quantity}, Requested: {transfer_data.quantity}",
            )

        # Get or create destination stock level
        dest_stock_result = db.execute(
            select(StockLevel)
            .where(
                StockLevel.product_id == transfer_data.product_id,
                StockLevel.warehouse_id == transfer_data.to_warehouse_id,
            )
            .with_for_update(skip_locked=True)
        )
        dest_stock = dest_stock_result.scalar_one_or_none()

        if not dest_stock:
            # Create destination stock level if it doesn't exist
            dest_stock = StockLevel(
                product_id=transfer_data.product_id,
                warehouse_id=transfer_data.to_warehouse_id,
                quantity=0,
                low_stock_threshold=10,  # Default threshold
            )
            db.add(dest_stock)
            db.flush()  # Ensure the new stock level gets an ID

        # Update quantities atomically
        source_stock.quantity -= transfer_data.quantity
        dest_stock.quantity += transfer_data.quantity

        # Create transfer record
        transfer = StockTransfer(
            product_id=transfer_data.product_id,
            from_warehouse_id=transfer_data.from_warehouse_id,
            to_warehouse_id=transfer_data.to_warehouse_id,
            quantity=transfer_data.quantity,
            notes=transfer_data.notes,
        )
        db.add(transfer)

        db.commit()
        db.refresh(transfer)

        # TODO: Record audit log entry
        # This would be implemented when the audit logging middleware is added

        return transfer

    except Exception as e:
        db.rollback()
        # Re-raise HTTPExceptions as-is
        if isinstance(e, HTTPException):
            raise
        # Wrap other exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transfer failed due to internal error",
        ) from e


@router.get("/transfers", response_model=PaginatedResponse[StockTransferResponse])
def get_transfer_history(
    page: int = 1,
    per_page: int = 50,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get stock transfer history with optional filters."""
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Build query with filters
    query = select(StockTransfer)

    if product_id:
        query = query.where(StockTransfer.product_id == product_id)
    if warehouse_id:
        query = query.where(
            (StockTransfer.from_warehouse_id == warehouse_id) | (StockTransfer.to_warehouse_id == warehouse_id)
        )

    # Get total count
    count_query = select(func.count(StockTransfer.id))
    if product_id:
        count_query = count_query.where(StockTransfer.product_id == product_id)
    if warehouse_id:
        count_query = count_query.where(
            (StockTransfer.from_warehouse_id == warehouse_id) | (StockTransfer.to_warehouse_id == warehouse_id)
        )

    total_result = db.execute(count_query)
    total = total_result.scalar()

    # Get transfers for current page
    transfers_result = db.execute(query.order_by(StockTransfer.created_at.desc()).offset(offset).limit(per_page))
    transfers = transfers_result.scalars().all()

    return {
        "items": transfers,
        "total": total,
        "page": page,
        "per_page": per_page,
    }
