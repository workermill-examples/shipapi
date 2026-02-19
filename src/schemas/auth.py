from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "demo@workermill.com",
                "password": "demo1234",
                "name": "Demo Admin",
            }
        }
    )

    email: EmailStr
    password: str
    name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be empty")
        return v


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "demo@workermill.com",
                "password": "demo1234",
            }
        }
    )

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": (
                    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
                    ".eyJzdWIiOiIxMjM0NTY3OC0xMjM0LTEyMzQtMTIzNC0xMjM0NTY3ODkwMTIiLCJlbWFpbCI6ImRlbW9Ad29ya2VybWlsbC5jb20iLCJyb2xlIjoiYWRtaW4iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzA4MzY4MDAwfQ"
                    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
                ),
                "refresh_token": (
                    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
                    ".eyJzdWIiOiIxMjM0NTY3OC0xMjM0LTEyMzQtMTIzNC0xMjM0NTY3ODkwMTIiLCJ0eXBlIjoicmVmcmVzaCIsImV4cCI6MTcwODk3MjgwMH0"
                    ".abc123refreshtokenexample"
                ),
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }
    )

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": (
                    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
                    ".eyJzdWIiOiIxMjM0NTY3OC0xMjM0LTEyMzQtMTIzNC0xMjM0NTY3ODkwMTIiLCJ0eXBlIjoicmVmcmVzaCIsImV4cCI6MTcwODk3MjgwMH0"
                    ".abc123refreshtokenexample"
                ),
            }
        }
    )

    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "12345678-1234-1234-1234-123456789012",
                "email": "demo@workermill.com",
                "name": "Demo Admin",
                "role": "admin",
                "created_at": "2026-01-01T00:00:00Z",
            }
        },
    )

    id: UUID
    email: str
    name: str
    role: str
    created_at: datetime


class RegisterResponse(UserResponse):
    """Returned once at registration — api_key is never shown again."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "12345678-1234-1234-1234-123456789012",
                "email": "demo@workermill.com",
                "name": "Demo Admin",
                "role": "admin",
                "created_at": "2026-01-01T00:00:00Z",
                "api_key": "sk_demo_shipapi_2026_showcase_key",
            }
        },
    )

    api_key: str
