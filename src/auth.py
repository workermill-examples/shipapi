"""JWT authentication, password hashing, and API key validation.

This module provides all authentication functionality:
- JWT encode/decode using PyJWT (NOT python-jose)
- Password hashing using bcrypt
- API key validation with SHA-256 hashing
- get_current_user dependency for FastAPI routes
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.models.user import User

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)

# JWT Configuration
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict | None:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_api_key() -> str:
    """Generate a new API key with sk_ prefix."""
    # Generate 32 random bytes and convert to hex
    key_data = secrets.token_hex(32)
    return f"sk_{key_data}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def get_user_by_api_key(api_key: str, db: Session) -> User | None:
    """Get user by API key."""
    api_key_hash = hash_api_key(api_key)
    result = db.execute(
        select(User).where(
            User.api_key_hash == api_key_hash,
            User.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


def get_user_by_id(user_id: str, db: Session) -> User | None:
    """Get user by ID."""
    result = db.execute(
        select(User).where(
            User.id == user_id,
            User.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token or API key.

    Supports two authentication methods:
    1. Authorization: Bearer <jwt_token>
    2. X-API-Key: sk_...

    This dependency is used in FastAPI routes that require authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = None

    # Try API key authentication first (from X-API-Key header)
    if x_api_key and x_api_key.startswith("sk_"):
        user = get_user_by_api_key(x_api_key, db)

    # Try JWT authentication if no API key or API key failed
    if user is None and credentials:
        token = credentials.credentials
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = get_user_by_id(str(user_id), db)

    if user is None:
        raise credentials_exception

    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current authenticated admin user.

    This dependency requires both authentication and admin privileges.
    Used in FastAPI routes that require admin access.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
