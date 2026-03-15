"""Authentication endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    generate_api_key,
    get_current_user,
    hash_api_key,
    hash_password,
    verify_password,
    verify_token,
)
from src.dependencies import get_db
from src.models.user import User
from src.schemas.user import ApiKeyResponse, LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserResponse

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Register a new user account.

    Creates a new user with hashed password. Email and username must be unique.
    Rate limited to 5 registrations per minute per IP.
    """
    # Check if user already exists
    existing_user = db.execute(
        select(User).where((User.email == user_data.email) | (User.username == user_data.username))
    ).scalar_one_or_none()

    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        else:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    # Create new user
    hashed_pw = hash_password(user_data.password)
    new_user = User(
        id=uuid.uuid4(),
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_pw,
        is_active=True,
        is_admin=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Returns both access and refresh tokens on successful authentication.
    Rate limited to 10 login attempts per minute per IP.
    """
    # Get user by email
    user = db.execute(
        select(User).where(
            User.email == login_data.email,
            User.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",  # noqa: S106
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh_token(request: Request, refresh_data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Validates the refresh token and generates a new access token.
    Rate limited to 30 refresh attempts per minute per IP.
    """
    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Verify user exists and is active
    user = db.execute(
        select(User).where(
            User.id == user_id,
            User.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Create new access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,  # Return the same refresh token
        token_type="bearer",  # noqa: S106
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """
    Get current user profile.

    Returns the authenticated user's profile information.
    Requires valid JWT token or API key authentication.
    """
    return UserResponse.model_validate(current_user)


@router.post("/api-key", response_model=ApiKeyResponse)
def generate_user_api_key(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ApiKeyResponse:
    """
    Generate a new API key for the current user.

    Returns the raw API key (only shown once) and stores its SHA-256 hash.
    Requires JWT authentication (not API key authentication).
    """
    # Generate new API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    # Update user with new API key hash
    current_user.api_key_hash = api_key_hash
    db.commit()

    return ApiKeyResponse(
        api_key=api_key,
        created_at=datetime.now(timezone.utc),
    )


@router.delete("/api-key")
def revoke_api_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Revoke the current user's API key.

    Clears the stored API key hash, invalidating the API key.
    Requires JWT authentication (not API key authentication).
    """
    current_user.api_key_hash = None
    db.commit()

    return {"detail": "API key revoked successfully"}
