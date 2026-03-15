"""FastAPI dependencies module.

Re-exports all common dependencies used across routers:
- get_db: Database session dependency
- get_current_user: Authentication dependency
- get_current_admin: Admin authentication dependency

Routers should import dependencies from this module for consistency.
"""

# Database dependency
# Authentication dependencies
from src.auth import get_current_admin, get_current_user
from src.database import get_db

__all__ = ["get_current_admin", "get_current_user", "get_db"]
