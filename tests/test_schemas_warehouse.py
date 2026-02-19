"""Tests for src/schemas/warehouse.py — WarehouseCreate, WarehouseUpdate,
WarehouseResponse, WarehouseDetailResponse."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.schemas.warehouse import (
    WarehouseCreate,
    WarehouseDetailResponse,
    WarehouseResponse,
    WarehouseUpdate,
)

# ---------------------------------------------------------------------------
# WarehouseCreate
# ---------------------------------------------------------------------------


def test_warehouse_create_valid():
    w = WarehouseCreate(name="Main", location="NYC", capacity=500)
    assert w.name == "Main"
    assert w.location == "NYC"
    assert w.capacity == 500


def test_warehouse_create_strips_whitespace():
    w = WarehouseCreate(name="  Main  ", location="  NYC  ", capacity=100)
    assert w.name == "Main"
    assert w.location == "NYC"


def test_warehouse_create_empty_name_raises():
    with pytest.raises(ValidationError):
        WarehouseCreate(name="   ", location="NYC", capacity=100)


def test_warehouse_create_empty_location_raises():
    with pytest.raises(ValidationError):
        WarehouseCreate(name="Main", location="   ", capacity=100)


def test_warehouse_create_zero_capacity_raises():
    with pytest.raises(ValidationError):
        WarehouseCreate(name="A", location="NYC", capacity=0)


def test_warehouse_create_negative_capacity_raises():
    with pytest.raises(ValidationError):
        WarehouseCreate(name="A", location="NYC", capacity=-1)


# ---------------------------------------------------------------------------
# WarehouseUpdate
# ---------------------------------------------------------------------------


def test_warehouse_update_all_optional():
    u = WarehouseUpdate()
    assert u.name is None
    assert u.location is None
    assert u.capacity is None
    assert u.is_active is None


def test_warehouse_update_partial_name():
    u = WarehouseUpdate(name="New Name")
    assert u.name == "New Name"
    assert u.capacity is None


def test_warehouse_update_strips_whitespace():
    u = WarehouseUpdate(name="  Trimmed  ", location="  Loc  ")
    assert u.name == "Trimmed"
    assert u.location == "Loc"


def test_warehouse_update_empty_name_raises():
    with pytest.raises(ValidationError):
        WarehouseUpdate(name="   ")


def test_warehouse_update_zero_capacity_raises():
    with pytest.raises(ValidationError):
        WarehouseUpdate(capacity=0)


def test_warehouse_update_is_active():
    u = WarehouseUpdate(is_active=False)
    assert u.is_active is False


# ---------------------------------------------------------------------------
# WarehouseResponse
# ---------------------------------------------------------------------------


def test_warehouse_response_from_orm():
    now = datetime.now(UTC)
    wid = uuid.uuid4()

    class FakeWarehouse:
        id = wid
        name = "Test Warehouse"
        location = "NYC"
        capacity = 100
        is_active = True
        created_at = now
        updated_at = now

    resp = WarehouseResponse.model_validate(FakeWarehouse())
    assert resp.id == wid
    assert resp.name == "Test Warehouse"
    assert resp.location == "NYC"
    assert resp.capacity == 100
    assert resp.is_active is True
    assert resp.created_at == now
    assert resp.updated_at == now


# ---------------------------------------------------------------------------
# WarehouseDetailResponse
# ---------------------------------------------------------------------------


def test_warehouse_detail_response_has_stock_summary():
    now = datetime.now(UTC)
    wid = uuid.uuid4()

    detail = WarehouseDetailResponse(
        id=wid,
        name="Detail Warehouse",
        location="LA",
        capacity=200,
        is_active=True,
        created_at=now,
        updated_at=now,
        total_products=5,
        total_quantity=120,
        capacity_utilization_pct=60.0,
    )
    assert detail.total_products == 5
    assert detail.total_quantity == 120
    assert detail.capacity_utilization_pct == 60.0


def test_warehouse_detail_inherits_base_fields():
    now = datetime.now(UTC)
    wid = uuid.uuid4()

    detail = WarehouseDetailResponse(
        id=wid,
        name="Detail",
        location="SF",
        capacity=500,
        is_active=True,
        created_at=now,
        updated_at=now,
        total_products=0,
        total_quantity=0,
        capacity_utilization_pct=0.0,
    )
    assert detail.id == wid
    assert detail.name == "Detail"
    assert detail.capacity == 500
