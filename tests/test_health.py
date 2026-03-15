"""Tests for health endpoint."""

from fastapi.testclient import TestClient


def test_health_endpoint_success(client: TestClient):
    """Test health endpoint returns 200 with service info."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()

    # Verify required fields
    assert "status" in data
    assert "database" in data
    assert "version" in data

    # Verify values
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"

    # Verify X-Request-Id header is present
    assert "X-Request-Id" in response.headers


def test_health_endpoint_includes_request_id(client: TestClient):
    """Test health endpoint includes X-Request-Id header."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert "X-Request-Id" in response.headers

    # Request ID should be a valid UUID format
    request_id = response.headers["X-Request-Id"]
    assert len(request_id) > 0
    # Basic UUID format check (contains hyphens)
    assert "-" in request_id


def test_health_endpoint_no_auth_required(client: TestClient):
    """Test health endpoint doesn't require authentication."""
    # Call without any auth headers
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
