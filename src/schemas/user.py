"""User-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Request schema for creating a new user."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=255, description="Username")
    password: str = Field(min_length=8, max_length=255, description="Password")


class UserResponse(BaseModel):
    """Response schema for user information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Response schema for JWT token responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str


class ApiKeyResponse(BaseModel):
    """Response schema for API key generation."""

    api_key: str
    created_at: datetime
