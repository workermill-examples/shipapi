"""Warehouse CRUD endpoints."""

import math
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user, get_db, require_admin
from src.models import User
from src.models.audit_log import AuditLog
from src.models.warehouse import Warehouse
from src.schemas.common import PaginatedResponse, Pagination
from src.schemas.stock import StockLevelResponse
from src.schemas.warehouse import (
    WarehouseCreate,
    WarehouseDetailResponse,
    WarehouseResponse,
    WarehouseUpdate,
)
from src.services.stock import get_warehouse_stock_summary, list_warehouse_stock

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


class _PaginationQuery(BaseModel):
    page: int = 1
    per_page: int = 20


@router.get("", response_model=PaginatedResponse[WarehouseResponse])
async def list_warehouses(
    q: Annotated[_PaginationQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[WarehouseResponse]:
    """Return a paginated list of all warehouses."""
    count_result = await db.execute(select(func.count()).select_from(Warehouse))
    total: int = count_result.scalar_one()

    offset = (q.page - 1) * q.per_page
    result = await db.execute(
        select(Warehouse).order_by(Warehouse.created_at.desc()).offset(offset).limit(q.per_page)
    )
    warehouses = list(result.scalars().all())

    total_pages = math.ceil(total / q.per_page) if q.per_page > 0 else 0
    return PaginatedResponse[WarehouseResponse](
        data=[WarehouseResponse.model_validate(w) for w in warehouses],
        pagination=Pagination(
            page=q.page, per_page=q.per_page, total=total, total_pages=total_pages
        ),
    )


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WarehouseResponse:
    """Create a new warehouse.  Admin only."""
    warehouse = Warehouse(
        name=body.name,
        location=body.location,
        capacity=body.capacity,
    )
    db.add(warehouse)
    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="create",
        resource_type="warehouse",
        resource_id=warehouse.id,
        changes={"name": body.name, "location": body.location, "capacity": body.capacity},
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(warehouse)
    return WarehouseResponse.model_validate(warehouse)


@router.get("/{warehouse_id}", response_model=WarehouseDetailResponse)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WarehouseDetailResponse:
    """Return warehouse detail with computed stock summary."""
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    total_products, total_quantity, capacity_utilization_pct = await get_warehouse_stock_summary(
        db, warehouse_id
    )

    return WarehouseDetailResponse(
        id=warehouse.id,
        name=warehouse.name,
        location=warehouse.location,
        capacity=warehouse.capacity,
        is_active=warehouse.is_active,
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
        total_products=total_products,
        total_quantity=total_quantity,
        capacity_utilization_pct=capacity_utilization_pct,
    )


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    body: WarehouseUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WarehouseResponse:
    """Update warehouse fields.  Admin only."""
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    warehouse = result.scalar_one_or_none()
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    changes: dict[str, Any] = {}
    if body.name is not None:
        changes["name"] = {"old": warehouse.name, "new": body.name}
        warehouse.name = body.name
    if body.location is not None:
        changes["location"] = {"old": warehouse.location, "new": body.location}
        warehouse.location = body.location
    if body.capacity is not None:
        changes["capacity"] = {"old": warehouse.capacity, "new": body.capacity}
        warehouse.capacity = body.capacity
    if body.is_active is not None:
        changes["is_active"] = {"old": warehouse.is_active, "new": body.is_active}
        warehouse.is_active = body.is_active

    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="update",
        resource_type="warehouse",
        resource_id=warehouse.id,
        changes=changes,
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(warehouse)
    return WarehouseResponse.model_validate(warehouse)


@router.get("/{warehouse_id}/stock", response_model=PaginatedResponse[StockLevelResponse])
async def list_warehouse_stock_levels(
    warehouse_id: uuid.UUID,
    q: Annotated[_PaginationQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[StockLevelResponse]:
    """Return paginated stock levels for a warehouse."""
    exists_result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    if exists_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    stock_levels, total = await list_warehouse_stock(db, warehouse_id, page=q.page, size=q.per_page)
    total_pages = math.ceil(total / q.per_page) if q.per_page > 0 else 0
    return PaginatedResponse[StockLevelResponse](
        data=[StockLevelResponse.model_validate(s) for s in stock_levels],
        pagination=Pagination(
            page=q.page, per_page=q.per_page, total=total, total_pages=total_pages
        ),
    )
