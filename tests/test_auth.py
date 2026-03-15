"""Tests for authentication endpoints."""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.auth import create_access_token, create_refresh_token, hash_password
from src.models.user import User


def test_register_success(client: TestClient):
    """Test successful user registration."""
    user_data = {
        "email": "newuser@test.com",
        "username": "newuser",
        "password": "password123"
    }

    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert data["is_active"] is True
    assert data["is_admin"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "X-Request-Id" in response.headers


def test_register_duplicate_email(client: TestClient):
    """Test registration fails with duplicate email."""
    user_data = {
        "email": "admin@test.com",  # Exists in seeded data
        "username": "newuser",
        "password": "password123"
    }

    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_register_duplicate_username(client: TestClient):
    """Test registration fails with duplicate username."""
    user_data = {
        "email": "newuser@test.com",
        "username": "admin_test",  # Exists in seeded data
        "password": "password123"
    }

    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already taken"


def test_register_invalid_email(client: TestClient):
    """Test registration fails with invalid email."""
    user_data = {
        "email": "invalid-email",
        "username": "newuser",
        "password": "password123"
    }

    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 422


def test_register_short_password(client: TestClient):
    """Test registration fails with short password."""
    user_data = {
        "email": "newuser@test.com",
        "username": "newuser",
        "password": "short"  # Less than 8 characters
    }

    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 422


def test_login_success(client: TestClient):
    """Test successful login."""
    login_data = {
        "email": "admin@test.com",
        "password": "admin123"
    }

    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 30 * 60  # 30 minutes in seconds
    assert "X-Request-Id" in response.headers


def test_login_invalid_credentials(client: TestClient):
    """Test login fails with invalid credentials."""
    login_data = {
        "email": "admin@test.com",
        "password": "wrongpassword"
    }

    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_user(client: TestClient):
    """Test login fails with nonexistent user."""
    login_data = {
        "email": "nonexistent@test.com",
        "password": "password123"
    }

    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_refresh_token_success(client: TestClient):
    """Test successful token refresh."""
    # First login to get tokens
    login_data = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    login_response = client.post("/api/v1/auth/login", json=login_data)
    tokens = login_response.json()

    # Use refresh token to get new access token
    refresh_data = {
        "refresh_token": tokens["refresh_token"]
    }

    response = client.post("/api/v1/auth/refresh", json=refresh_data)

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 30 * 60
    # Should return the same refresh token
    assert data["refresh_token"] == tokens["refresh_token"]
    # Should return a new access token
    assert data["access_token"] != tokens["access_token"]


def test_refresh_token_invalid(client: TestClient):
    """Test refresh fails with invalid token."""
    refresh_data = {
        "refresh_token": "invalid_token"
    }

    response = client.post("/api/v1/auth/refresh", json=refresh_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


def test_refresh_token_expired(client: TestClient):
    """Test refresh fails with expired token."""
    # Create an expired token
    user_id = "11111111-1111-1111-1111-111111111111"

    # Mock datetime to create an expired token
    past_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    with patch("src.auth.datetime") as mock_datetime:
        mock_datetime.now.return_value = past_time
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        expired_token = create_refresh_token(data={"sub": user_id})

    refresh_data = {
        "refresh_token": expired_token
    }

    response = client.post("/api/v1/auth/refresh", json=refresh_data)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


def test_get_current_user_with_jwt(client: TestClient, admin_headers: dict[str, str]):
    """Test getting current user profile with JWT token."""
    response = client.get("/api/v1/auth/me", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "admin@test.com"
    assert data["username"] == "admin_test"
    assert data["is_admin"] is True
    assert data["is_active"] is True


def test_get_current_user_no_auth(client: TestClient):
    """Test getting current user fails without authentication."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_get_current_user_invalid_token(client: TestClient):
    """Test getting current user fails with invalid token."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_generate_api_key_success(client: TestClient, admin_headers: dict[str, str]):
    """Test successful API key generation."""
    response = client.post("/api/v1/auth/api-key", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert "api_key" in data
    assert data["api_key"].startswith("sk_")
    assert "created_at" in data
    assert len(data["api_key"]) > 10  # Should be a long key


def test_generate_api_key_no_auth(client: TestClient):
    """Test API key generation fails without authentication."""
    response = client.post("/api/v1/auth/api-key")

    assert response.status_code == 401


def test_revoke_api_key_success(client: TestClient, admin_headers: dict[str, str]):
    """Test successful API key revocation."""
    # First generate an API key
    client.post("/api/v1/auth/api-key", headers=admin_headers)

    # Then revoke it
    response = client.delete("/api/v1/auth/api-key", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["detail"] == "API key revoked successfully"


def test_revoke_api_key_no_auth(client: TestClient):
    """Test API key revocation fails without authentication."""
    response = client.delete("/api/v1/auth/api-key")

    assert response.status_code == 401


def test_api_key_authentication(client: TestClient, admin_headers: dict[str, str], db):
    """Test authentication using API key."""
    # Generate an API key
    response = client.post("/api/v1/auth/api-key", headers=admin_headers)
    api_key = response.json()["api_key"]

    # Use API key for authentication
    api_headers = {"X-API-Key": api_key}
    response = client.get("/api/v1/auth/me", headers=api_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"


def test_api_key_authentication_invalid_key(client: TestClient):
    """Test authentication fails with invalid API key."""
    api_headers = {"X-API-Key": "sk_invalid_key"}
    response = client.get("/api/v1/auth/me", headers=api_headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_api_key_authentication_wrong_prefix(client: TestClient):
    """Test authentication fails with wrong API key prefix."""
    api_headers = {"X-API-Key": "ak_wrongprefix"}
    response = client.get("/api/v1/auth/me", headers=api_headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_api_key_after_revocation(client: TestClient, admin_headers: dict[str, str]):
    """Test API key doesn't work after revocation."""
    # Generate an API key
    response = client.post("/api/v1/auth/api-key", headers=admin_headers)
    api_key = response.json()["api_key"]

    # Verify it works
    api_headers = {"X-API-Key": api_key}
    response = client.get("/api/v1/auth/me", headers=api_headers)
    assert response.status_code == 200

    # Revoke the API key
    client.delete("/api/v1/auth/api-key", headers=admin_headers)

    # Verify it no longer works
    response = client.get("/api/v1/auth/me", headers=api_headers)
    assert response.status_code == 401


def test_auth_endpoints_have_prefix(client: TestClient):
    """Test all auth endpoints are under /api/v1/auth prefix."""
    # Test a few endpoints to ensure they're properly prefixed

    # Should work
    response = client.post("/api/v1/auth/login", json={"email": "test", "password": "test"})
    assert response.status_code in [401, 422]  # Not 404

    # Should not work (wrong prefix)
    response = client.post("/auth/login", json={"email": "test", "password": "test"})
    assert response.status_code == 404