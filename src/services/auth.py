"""Authentication service: JWT tokens, password hashing, and API key operations."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from src.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password* using 12 cost rounds."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if *password* matches *password_hash*."""
    return _pwd_context.verify(password, password_hash)


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


def generate_api_key() -> str:
    """Return a new API key: ``sk_`` followed by 64 random hex characters."""
    return "sk_" + secrets.token_hex(32)


def hash_api_key(api_key: str) -> str:
    """Return the SHA-256 hex digest of *api_key* for safe storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Return True if *api_key* matches *stored_hash* (constant-time comparison)."""
    computed = hashlib.sha256(api_key.encode()).hexdigest()
    return secrets.compare_digest(computed, stored_hash)


def get_api_key_prefix(api_key: str) -> str:
    """Return the first 8 characters of *api_key* for display/identification."""
    return api_key[:8]


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Return a signed HS256 JWT access token valid for *access_token_expire_minutes*."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Return a signed HS256 JWT refresh token valid for *refresh_token_expire_days*.

    The ``type`` claim is set to ``"refresh"`` so that the refresh endpoint can
    reject tokens issued as access tokens (and vice-versa).
    """
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and verify *token*.  Raises :exc:`jose.JWTError` if invalid or expired."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
