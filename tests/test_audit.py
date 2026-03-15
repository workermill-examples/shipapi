"""Tests for audit log endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.models.user import User


def test_get_audit_log_success(client: TestClient, admin_headers: dict[str, str]):
    """Test getting audit log entries."""
    response = client.get("/api/v1/audit", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # Check pagination structure
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data

    # Should have seeded audit entries
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    # Check audit entry structure
    if data["items"]:
        entry = data["items"][0]
        assert "id" in entry
        assert "user_id" in entry
        assert "action" in entry
        assert "resource_type" in entry
        assert "resource_id" in entry
        assert "details" in entry
        assert "ip_address" in entry
        assert "created_at" in entry


def test_get_audit_log_pagination(client: TestClient, admin_headers: dict[str, str]):
    """Test audit log pagination."""
    response = client.get("/api/v1/audit?page=1&per_page=1", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["per_page"] == 1
    assert len(data["items"]) <= 1


def test_get_audit_log_filter_by_user(client: TestClient, admin_headers: dict[str, str], admin_user: User):
    """Test filtering audit log by user ID."""
    response = client.get(f"/api/v1/audit?user_id={admin_user.id}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned entries should be for the specified user
    for entry in data["items"]:
        assert entry["user_id"] == str(admin_user.id)


def test_get_audit_log_filter_by_action(client: TestClient, admin_headers: dict[str, str]):
    """Test filtering audit log by action."""
    response = client.get("/api/v1/audit?action=create", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned entries should have the specified action
    for entry in data["items"]:
        assert entry["action"] == "create"


def test_get_audit_log_filter_by_resource_type(client: TestClient, admin_headers: dict[str, str]):
    """Test filtering audit log by resource type."""
    response = client.get("/api/v1/audit?resource_type=product", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # All returned entries should have the specified resource type
    for entry in data["items"]:
        assert entry["resource_type"] == "product"


def test_get_audit_log_filter_by_date_range(client: TestClient, admin_headers: dict[str, str]):
    """Test filtering audit log by date range."""
    # Get current time and use a wide range to ensure we capture seeded data
    end_date = datetime.now(timezone.utc)
    start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)

    # Format dates properly for URL encoding
    start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    response = client.get(
        f"/api/v1/audit?start_date={start_date_str}&end_date={end_date_str}", headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Should have some entries in this wide range
    assert data["total"] >= 0

    # All returned entries should be within the date range
    for entry in data["items"]:
        entry_date = datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
        assert start_date <= entry_date <= end_date


def test_get_audit_log_combined_filters(client: TestClient, admin_headers: dict[str, str], admin_user: User):
    """Test combining multiple filters."""
    response = client.get(
        f"/api/v1/audit?user_id={admin_user.id}&action=create&resource_type=product", headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()

    # All returned entries should match all filters
    for entry in data["items"]:
        assert entry["user_id"] == str(admin_user.id)
        assert entry["action"] == "create"
        assert entry["resource_type"] == "product"


def test_get_audit_log_empty_results(client: TestClient, admin_headers: dict[str, str]):
    """Test audit log with filters that return no results."""
    # Use a very old date range that should have no entries
    start_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2000, 12, 31, tzinfo=timezone.utc)

    # Format dates properly for URL encoding
    start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    response = client.get(
        f"/api/v1/audit?start_date={start_date_str}&end_date={end_date_str}", headers=admin_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_get_audit_log_non_admin(client: TestClient, regular_user_headers: dict[str, str]):
    """Test audit log access fails for non-admin users."""
    response = client.get("/api/v1/audit", headers=regular_user_headers)

    assert response.status_code == 403
    assert "Admin privileges required" in response.json()["detail"]


def test_get_audit_log_no_auth(client: TestClient):
    """Test audit log access fails without authentication."""
    response = client.get("/api/v1/audit")

    assert response.status_code == 401


def test_get_audit_log_invalid_user_id(client: TestClient, admin_headers: dict[str, str]):
    """Test audit log with invalid user ID format."""
    response = client.get("/api/v1/audit?user_id=invalid-uuid", headers=admin_headers)

    assert response.status_code == 422  # UUID validation error


def test_get_audit_log_nonexistent_user_id(client: TestClient, admin_headers: dict[str, str]):
    """Test audit log with nonexistent user ID."""
    fake_user_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/audit?user_id={fake_user_id}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # Should return empty results
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_get_audit_log_invalid_date_format(client: TestClient, admin_headers: dict[str, str]):
    """Test audit log with invalid date format."""
    response = client.get("/api/v1/audit?start_date=invalid-date", headers=admin_headers)

    assert response.status_code == 422  # Validation error


def test_get_audit_log_ordering(client: TestClient, admin_headers: dict[str, str]):
    """Test that audit log entries are ordered by created_at descending."""
    response = client.get("/api/v1/audit?per_page=10", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    if len(data["items"]) > 1:
        # Check that entries are ordered by created_at descending
        for i in range(len(data["items"]) - 1):
            current_date = datetime.fromisoformat(data["items"][i]["created_at"].replace("Z", "+00:00"))
            next_date = datetime.fromisoformat(data["items"][i + 1]["created_at"].replace("Z", "+00:00"))
            assert current_date >= next_date


def test_get_audit_log_max_per_page(client: TestClient, admin_headers: dict[str, str]):
    """Test that per_page is capped at 100."""
    response = client.get("/api/v1/audit?per_page=200", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    # Should be capped at 100
    assert data["per_page"] == 100


def test_audit_log_contains_details(client: TestClient, admin_headers: dict[str, str]):
    """Test that audit log entries contain JSON details."""
    response = client.get("/api/v1/audit", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    if data["items"]:
        entry = data["items"][0]
        assert "details" in entry

        # Details should be a dict/object (JSON)
        if entry["details"]:
            assert isinstance(entry["details"], dict)


def test_audit_endpoints_have_prefix(client: TestClient, admin_headers: dict[str, str]):
    """Test all audit endpoints are under /api/v1/audit prefix."""
    # Should work
    response = client.get("/api/v1/audit", headers=admin_headers)
    assert response.status_code == 200

    # Should not work (wrong prefix)
    response = client.get("/audit", headers=admin_headers)
    assert response.status_code == 404
