"""Warehouses API endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.dependencies import get_current_admin, get_current_user, get_db
from src.models import StockLevel, Warehouse
from src.schemas import PaginatedResponse, WarehouseCreate, WarehouseResponse, WarehouseUpdate
from src.schemas.warehouse import StockSummary

router = APIRouter(prefix="/api/v1/warehouses", tags=["Warehouses"])


@router.get("", response_model=PaginatedResponse[WarehouseResponse])
def list_warehouses(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """List all warehouses with pagination."""
    per_page = min(per_page, 100)

    offset = (page - 1) * per_page

    # Get total count
    total_result = db.execute(select(func.count(Warehouse.id)))
    total = total_result.scalar()

    # Get warehouses for current page
    warehouses_result = db.execute(select(Warehouse).order_by(Warehouse.name).offset(offset).limit(per_page))
    warehouses = warehouses_result.scalars().all()

    # Compute stock summaries for each warehouse
    warehouse_responses = []
    for warehouse in warehouses:
        # Calculate stock summary using func.count and func.sum
        result = db.execute(
            select(
                func.count(StockLevel.id).label("total_items"),
                func.coalesce(func.sum(StockLevel.quantity), 0).label("total_quantity"),
            ).where(StockLevel.warehouse_id == warehouse.id)
        )
        summary = result.one()

        # Create stock summary
        stock_summary = StockSummary(
            total_items=summary.total_items,
            total_quantity=summary.total_quantity,
        )

        # Convert to response model and add stock summary
        response_data = WarehouseResponse.model_validate(warehouse)
        response_data.stock_summary = stock_summary
        warehouse_responses.append(response_data)

    return {
        "items": warehouse_responses,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> Warehouse:
    """Create a new warehouse (admin only)."""
    # Create warehouse
    warehouse = Warehouse(
        name=warehouse_data.name,
        code=warehouse_data.code,
        address=warehouse_data.address,
    )

    db.add(warehouse)
    try:
        db.commit()
        db.refresh(warehouse)
        return warehouse
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Warehouse with this code already exists"
        ) from e


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(
    warehouse_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: Any = Depends(get_current_user),
) -> WarehouseResponse:
    """Get a warehouse by ID with stock level summary."""
    # Get the warehouse
    warehouse_result = db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = warehouse_result.scalar_one_or_none()

    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    # Calculate stock summary using func.count and func.sum
    result = db.execute(
        select(
            func.count(StockLevel.id).label("total_items"),
            func.coalesce(func.sum(StockLevel.quantity), 0).label("total_quantity"),
        ).where(StockLevel.warehouse_id == warehouse.id)
    )
    summary = result.one()

    # Create stock summary
    stock_summary = StockSummary(
        total_items=summary.total_items,
        total_quantity=summary.total_quantity,
    )

    # Convert to response model and add stock summary
    response_data = WarehouseResponse.model_validate(warehouse)
    response_data.stock_summary = stock_summary

    return response_data


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: uuid.UUID,
    warehouse_data: WarehouseUpdate,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> Warehouse:
    """Update a warehouse (admin only)."""
    # Get existing warehouse
    warehouse_result = db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = warehouse_result.scalar_one_or_none()

    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    # Update fields
    if warehouse_data.name is not None:
        warehouse.name = warehouse_data.name
    if warehouse_data.code is not None:
        warehouse.code = warehouse_data.code
    if warehouse_data.address is not None:
        warehouse.address = warehouse_data.address
    if warehouse_data.is_active is not None:
        warehouse.is_active = warehouse_data.is_active

    try:
        db.commit()
        db.refresh(warehouse)
        return warehouse
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Warehouse with this code already exists"
        ) from e


@router.delete("/{warehouse_id}")
def delete_warehouse(
    warehouse_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_admin: Any = Depends(get_current_admin),
) -> dict[str, str]:
    """Delete a warehouse (admin only). Cannot delete if it has stock levels."""
    # Get warehouse
    warehouse_result = db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = warehouse_result.scalar_one_or_none()

    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    # Check if warehouse has stock levels
    stock_count_result = db.execute(select(func.count(StockLevel.id)).where(StockLevel.warehouse_id == warehouse.id))
    stock_count = stock_count_result.scalar() or 0

    if stock_count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete warehouse with stock levels")

    # Delete warehouse
    db.delete(warehouse)
    db.commit()

    return {"detail": "Warehouse deleted successfully"}
