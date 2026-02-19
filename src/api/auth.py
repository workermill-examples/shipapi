"""Authentication endpoints: register, login, refresh tokens, and current-user profile."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.dependencies import get_current_user, get_db
from src.middleware.rate_limit import get_user_key, limiter
from src.models import User
from src.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from src.schemas.common import ErrorResponse
from src.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password",
    headers={"WWW-Authenticate": "Bearer"},
)

_INVALID_REFRESH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired refresh token",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RegisterResponse:
    """Register a new user account.

    Generates a one-time API key returned only in this response.
    Returns 409 if the email address is already registered.
    Rate limited: 5 requests per minute per IP address.
    """
    raw_api_key = generate_api_key()
    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        api_key_hash=hash_api_key(raw_api_key),
        api_key_prefix=raw_api_key[:8],
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    return RegisterResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at,
        api_key=raw_api_key,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid email or password"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Authenticate with email and password.

    Returns a JWT access token (30-minute lifetime) and a refresh token
    (7-day lifetime) on success.
    Rate limited: 10 requests per minute per IP address.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise _INVALID_CREDENTIALS

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email, user.role),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Exchange a valid refresh token for new access and refresh tokens.

    Refresh tokens are single-use — each call issues a fresh pair.
    Returns 401 if the token is missing, expired, or not a refresh token.
    Rate limited: 30 requests per minute per IP address.
    """
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise _INVALID_REFRESH from None

    if payload.get("type") != "refresh":
        raise _INVALID_REFRESH

    raw_id: str | None = payload.get("sub")
    if not raw_id:
        raise _INVALID_REFRESH

    try:
        user_id = uuid.UUID(raw_id)
    except ValueError:
        raise _INVALID_REFRESH from None

    user: User | None = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _INVALID_REFRESH

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.email, user.role),
        refresh_token=create_refresh_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("100/minute", key_func=get_user_key)
async def me(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> UserResponse:
    """Return the authenticated user's profile.

    Rate limited: 100 requests per minute per authenticated user.
    """
    return UserResponse.model_validate(current_user)
