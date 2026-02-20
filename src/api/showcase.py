"""Showcase endpoints — public stats API and HTML landing page."""

import pathlib

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import AuditLog, Category, Product, StockLevel, StockTransfer, Warehouse
from src.schemas.showcase import ShowcaseStats

router = APIRouter(prefix="/showcase", tags=["Showcase"])
root_router = APIRouter()

_TEMPLATE_PATH = pathlib.Path(__file__).parent.parent / "templates" / "landing.html"
_LANDING_HTML: str = _TEMPLATE_PATH.read_text(encoding="utf-8")


@router.get(
    "/stats",
    response_model=ShowcaseStats,
    summary="Public showcase statistics",
    description="Returns aggregate counts for the showcase landing page. No authentication required.",
)
async def get_showcase_stats(db: AsyncSession = Depends(get_db)) -> ShowcaseStats:  # noqa: B008
    """Return aggregate counts across all core resources in a single SQL round-trip."""
    result = await db.execute(
        select(
            select(func.count())
            .where(Product.is_active.is_(True))
            .scalar_subquery()
            .label("products"),
            select(func.count()).select_from(Category).scalar_subquery().label("categories"),
            select(func.count())
            .where(Warehouse.is_active.is_(True))
            .scalar_subquery()
            .label("warehouses"),
            select(func.count())
            .where(StockLevel.quantity < StockLevel.min_threshold)
            .scalar_subquery()
            .label("stock_alerts"),
            select(func.count())
            .select_from(StockTransfer)
            .scalar_subquery()
            .label("stock_transfers"),
            select(func.count()).select_from(AuditLog).scalar_subquery().label("audit_log_entries"),
        )
    )
    row = result.one()
    return ShowcaseStats(
        products=row.products,
        categories=row.categories,
        warehouses=row.warehouses,
        stock_alerts=row.stock_alerts,
        stock_transfers=row.stock_transfers,
        audit_log_entries=row.audit_log_entries,
    )


@root_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page() -> str:
    """Serve the ShipAPI showcase landing page."""
    return _LANDING_HTML
