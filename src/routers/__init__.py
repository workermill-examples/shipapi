"""FastAPI routers package."""

from . import audit, auth, categories, health, products, showcase, stock, warehouses

__all__ = ["auth", "health", "categories", "products", "warehouses", "stock", "audit", "showcase"]
