"""Main API router — mounts all sub-routers under /api/v1."""

from fastapi import APIRouter

from src.api.audit import router as audit_router
from src.api.auth import router as auth_router
from src.api.categories import router as categories_router
from src.api.health import router as health_router
from src.api.products import router as products_router
from src.api.stock import router as stock_router
from src.api.warehouses import router as warehouses_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(categories_router)
api_router.include_router(products_router)
api_router.include_router(warehouses_router)
api_router.include_router(stock_router)
