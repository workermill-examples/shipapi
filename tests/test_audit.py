"""Tests for the audit subsystem: service functions and GET /audit-log endpoint."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.audit import router as audit_router
from src.database import get_db
from src.models import AuditLog, User
from src.schemas.audit import AuditLogQuery
from src.services.audit import list_audit_logs, record_audit_log
from src.services.auth import create_access_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, role: str = "admin", is_active: bool = True) -> MagicMock:
    """Return a MagicMock shaped like a User ORM instance."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.name = "Admin"
    user.role = role
    user.is_active = is_active
    user.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    return user


def _make_audit_log(
    *,
    action: str = "create",
    resource_type: str = "product",
    changes: dict | None = None,
    ip_address: str | None = "127.0.0.1",
) -> MagicMock:
    """Return a MagicMock shaped like an AuditLog ORM instance."""
    log = MagicMock(spec=AuditLog)
    log.id = uuid.uuid4()
    log.user_id = uuid.uuid4()
    log.action = action
    log.resource_type = resource_type
    log.resource_id = uuid.uuid4()
    log.changes = changes
    log.ip_address = ip_address
    log.created_at = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
    return log


def _make_app(db_mock: Any) -> FastAPI:
    """Build a minimal FastAPI app with the audit router and overridden DB."""
    app = FastAPI()
    app.include_router(audit_router)

    async def override_get_db() -> AsyncGenerator[Any]:
        yield db_mock

    app.dependency_overrides[get_db] = override_get_db
    return app


# ---------------------------------------------------------------------------
# record_audit_log service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_audit_log_creates_and_returns_record() -> None:
    """record_audit_log adds an AuditLog to DB, commits, and returns it."""
    audit_log = _make_audit_log()

    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock(side_effect=lambda obj: None)

    await record_audit_log(
        db_mock,
        user_id=audit_log.user_id,
        action="create",
        resource_type="product",
        resource_id=audit_log.resource_id,
        changes={"name": {"old": None, "new": "Widget A"}},
        ip_address="10.0.0.1",
    )

    db_mock.add.assert_called_once()
    db_mock.commit.assert_awaited_once()
    db_mock.refresh.assert_awaited_once()
    added = db_mock.add.call_args[0][0]
    assert isinstance(added, AuditLog)
    assert added.action == "create"
    assert added.resource_type == "product"
    assert added.ip_address == "10.0.0.1"


@pytest.mark.asyncio
async def test_record_audit_log_without_optional_fields() -> None:
    """record_audit_log accepts None for changes and ip_address."""
    user_id = uuid.uuid4()
    resource_id = uuid.uuid4()

    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    await record_audit_log(
        db_mock,
        user_id=user_id,
        action="delete",
        resource_type="warehouse",
        resource_id=resource_id,
    )

    added = db_mock.add.call_args[0][0]
    assert added.changes is None
    assert added.ip_address is None


# ---------------------------------------------------------------------------
# list_audit_logs service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_audit_logs_returns_logs_and_total() -> None:
    """list_audit_logs returns (logs, total) for an unfiltered query."""
    log1 = _make_audit_log()
    log2 = _make_audit_log(action="delete")

    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log1, log2]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    query = AuditLogQuery(page=1, per_page=20)
    logs, total = await list_audit_logs(db_mock, query)

    assert total == 2
    assert len(logs) == 2
    assert db_mock.execute.await_count == 2


@pytest.mark.asyncio
async def test_list_audit_logs_with_action_filter() -> None:
    """list_audit_logs applies action filter to both count and data queries."""
    log = _make_audit_log(action="update")

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    query = AuditLogQuery(action="update")
    logs, total = await list_audit_logs(db_mock, query)

    assert total == 1
    assert logs[0].action == "update"


@pytest.mark.asyncio
async def test_list_audit_logs_with_resource_type_filter() -> None:
    """list_audit_logs applies resource_type filter."""
    log = _make_audit_log(resource_type="category")

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    query = AuditLogQuery(resource_type="category")
    logs, total = await list_audit_logs(db_mock, query)

    assert total == 1
    assert logs[0].resource_type == "category"


@pytest.mark.asyncio
async def test_list_audit_logs_with_user_id_filter() -> None:
    """list_audit_logs applies user_id filter."""
    target_user_id = uuid.uuid4()
    log = _make_audit_log()
    log.user_id = target_user_id

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    query = AuditLogQuery(user_id=target_user_id)
    logs, total = await list_audit_logs(db_mock, query)

    assert total == 1
    assert logs[0].user_id == target_user_id


@pytest.mark.asyncio
async def test_list_audit_logs_with_date_range_filter() -> None:
    """list_audit_logs applies start_date and end_date filters."""
    log = _make_audit_log()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    query = AuditLogQuery(
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 12, 31, tzinfo=UTC),
    )
    logs, total = await list_audit_logs(db_mock, query)

    assert total == 1
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_list_audit_logs_empty_result() -> None:
    """list_audit_logs returns empty list and zero total when no matches."""
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    query = AuditLogQuery(action="transfer")
    logs, total = await list_audit_logs(db_mock, query)

    assert total == 0
    assert logs == []


# ---------------------------------------------------------------------------
# GET /audit-log endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_audit_log_returns_paginated_response() -> None:
    """Admin user receives paginated audit log response."""
    admin = _make_user(role="admin")
    log = _make_audit_log()
    token = create_access_token(str(admin.id), admin.email, admin.role)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/audit-log",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["total"] == 1
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["per_page"] == 20
    assert data["pagination"]["total_pages"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["action"] == "create"
    assert data["data"][0]["resource_type"] == "product"


@pytest.mark.asyncio
async def test_get_audit_log_unauthenticated_returns_401() -> None:
    """Request without auth token returns 401."""
    db_mock = AsyncMock()
    app = _make_app(db_mock)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/audit-log")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_audit_log_non_admin_returns_403() -> None:
    """Non-admin user receives 403 Forbidden."""
    regular_user = _make_user(role="user")
    token = create_access_token(str(regular_user.id), regular_user.email, regular_user.role)

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=regular_user)

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/audit-log",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_audit_log_with_action_filter() -> None:
    """Admin can filter audit log by action query parameter."""
    admin = _make_user(role="admin")
    token = create_access_token(str(admin.id), admin.email, admin.role)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/audit-log",
            params={"action": "delete"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 0
    assert data["data"] == []


@pytest.mark.asyncio
async def test_get_audit_log_pagination_params() -> None:
    """Pagination parameters page and per_page are respected."""
    admin = _make_user(role="admin")
    token = create_access_token(str(admin.id), admin.email, admin.role)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 50

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/audit-log",
            params={"page": 3, "per_page": 10},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["page"] == 3
    assert data["pagination"]["per_page"] == 10
    assert data["pagination"]["total"] == 50
    assert data["pagination"]["total_pages"] == 5


@pytest.mark.asyncio
async def test_get_audit_log_with_resource_type_filter() -> None:
    """Admin can filter by resource_type query parameter."""
    admin = _make_user(role="admin")
    log = _make_audit_log(resource_type="warehouse")
    token = create_access_token(str(admin.id), admin.email, admin.role)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/audit-log",
            params={"resource_type": "warehouse"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["data"][0]["resource_type"] == "warehouse"


@pytest.mark.asyncio
async def test_get_audit_log_with_user_id_filter() -> None:
    """Admin can filter by user_id query parameter."""
    admin = _make_user(role="admin")
    target_user_id = uuid.uuid4()
    log = _make_audit_log()
    log.user_id = target_user_id
    token = create_access_token(str(admin.id), admin.email, admin.role)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/audit-log",
            params={"user_id": str(target_user_id)},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 1


@pytest.mark.asyncio
async def test_get_audit_log_response_fields() -> None:
    """Audit log response contains all required AuditLogResponse fields."""
    admin = _make_user(role="admin")
    log = _make_audit_log(
        action="update",
        resource_type="product",
        changes={"name": {"old": "Old Name", "new": "New Name"}},
        ip_address="192.168.1.1",
    )
    token = create_access_token(str(admin.id), admin.email, admin.role)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [log]
    logs_result = MagicMock()
    logs_result.scalars.return_value = scalars_mock

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=admin)
    db_mock.execute = AsyncMock(side_effect=[count_result, logs_result])

    app = _make_app(db_mock)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/audit-log",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    entry = response.json()["data"][0]
    assert "id" in entry
    assert "user_id" in entry
    assert "action" in entry
    assert "resource_type" in entry
    assert "resource_id" in entry
    assert "changes" in entry
    assert "ip_address" in entry
    assert "created_at" in entry
    assert entry["action"] == "update"
    assert entry["resource_type"] == "product"
    assert entry["changes"] == {"name": {"old": "Old Name", "new": "New Name"}}
    assert entry["ip_address"] == "192.168.1.1"
