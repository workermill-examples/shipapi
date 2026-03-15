"""Showcase API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Category, Product, StockLevel, StockTransfer, Warehouse

router = APIRouter(prefix="/showcase", tags=["Showcase"])


@router.get("/stats")
def get_showcase_stats(db: Session = Depends(get_db)) -> dict[str, int]:
    """Live DB metrics for showcase display (no auth required)."""
    # Count total products
    total_products_result = db.execute(select(func.count(Product.id)))
    total_products = total_products_result.scalar()

    # Count total categories
    total_categories_result = db.execute(select(func.count(Category.id)))
    total_categories = total_categories_result.scalar()

    # Count total warehouses
    total_warehouses_result = db.execute(select(func.count(Warehouse.id)))
    total_warehouses = total_warehouses_result.scalar()

    # Count total stock transfers
    total_stock_transfers_result = db.execute(select(func.count(StockTransfer.id)))
    total_stock_transfers = total_stock_transfers_result.scalar()

    # Count low stock alerts (quantity < low_stock_threshold)
    low_stock_alerts_result = db.execute(
        select(func.count(StockLevel.id)).where(StockLevel.quantity < StockLevel.low_stock_threshold)
    )
    low_stock_alerts = low_stock_alerts_result.scalar()

    return {
        "total_products": total_products,
        "total_categories": total_categories,
        "total_warehouses": total_warehouses,
        "total_stock_transfers": total_stock_transfers,
        "low_stock_alerts": low_stock_alerts,
    }
