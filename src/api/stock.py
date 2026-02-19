"""Stock management endpoints: upsert stock levels, atomic transfers, and low-stock alerts."""

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_current_user, get_db
from src.models import User
from src.schemas.common import ErrorResponse, PaginatedResponse, Pagination
from src.schemas.stock import (
    StockAlertResponse,
    StockLevelResponse,
    StockUpdateRequest,
    TransferRequest,
    TransferResponse,
)
from src.services.stock import get_stock_alerts, transfer_stock, upsert_stock_level

router = APIRouter(prefix="/stock", tags=["Stock"])


class _PaginationQuery(BaseModel):
    page: int = 1
    per_page: int = 20


@router.put(
    "/{product_id}/{warehouse_id}",
    response_model=StockLevelResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Warehouse is not active"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Product or warehouse not found"},
        409: {"model": ErrorResponse, "description": "Concurrent update conflict — retry"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def update_stock_level(
    product_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    body: StockUpdateRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StockLevelResponse:
    """Create or update the stock level for a product in a warehouse."""
    stock_level = await upsert_stock_level(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        request=body,
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return StockLevelResponse.model_validate(stock_level)


@router.post(
    "/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Insufficient stock in source warehouse"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {
            "model": ErrorResponse,
            "description": "Product or source/destination warehouse not found or inactive",
        },
        422: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def create_transfer(
    body: TransferRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransferResponse:
    """Atomically transfer stock from one warehouse to another."""
    transfer = await transfer_stock(
        db,
        request=body,
        current_user=current_user,
        ip_address=request.client.host if request.client else None,
    )
    return TransferResponse.model_validate(transfer)


@router.get(
    "/alerts",
    response_model=PaginatedResponse[StockAlertResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_stock_alerts(
    q: Annotated[_PaginationQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[StockAlertResponse]:
    """Return stock levels below their minimum threshold, sorted by deficit (descending)."""
    stock_levels, total = await get_stock_alerts(db, page=q.page, size=q.per_page)
    total_pages = math.ceil(total / q.per_page) if q.per_page > 0 else 0
    alerts = [
        StockAlertResponse(
            product=stock.product,
            warehouse=stock.warehouse,
            quantity=stock.quantity,
            min_threshold=stock.min_threshold,
            deficit=stock.min_threshold - stock.quantity,
        )
        for stock in stock_levels
    ]
    return PaginatedResponse[StockAlertResponse](
        data=alerts,
        pagination=Pagination(
            page=q.page, per_page=q.per_page, total=total, total_pages=total_pages
        ),
    )
