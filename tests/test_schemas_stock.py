"""Tests for src/schemas/stock.py — StockUpdateRequest, StockLevelResponse,
TransferRequest, TransferResponse, StockAlertResponse."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.schemas.stock import (
    ProductSummary,
    StockAlertResponse,
    StockLevelResponse,
    StockUpdateRequest,
    TransferRequest,
    TransferResponse,
    WarehouseSummary,
)

# ---------------------------------------------------------------------------
# StockUpdateRequest
# ---------------------------------------------------------------------------


def test_stock_update_request_valid():
    req = StockUpdateRequest(quantity=50)
    assert req.quantity == 50
    assert req.min_threshold is None


def test_stock_update_request_with_threshold():
    req = StockUpdateRequest(quantity=50, min_threshold=10)
    assert req.min_threshold == 10


def test_stock_update_request_zero_quantity_valid():
    req = StockUpdateRequest(quantity=0)
    assert req.quantity == 0


def test_stock_update_request_negative_quantity_raises():
    with pytest.raises(ValidationError):
        StockUpdateRequest(quantity=-1)


def test_stock_update_request_zero_threshold_valid():
    req = StockUpdateRequest(quantity=5, min_threshold=0)
    assert req.min_threshold == 0


def test_stock_update_request_negative_threshold_raises():
    with pytest.raises(ValidationError):
        StockUpdateRequest(quantity=5, min_threshold=-1)


# ---------------------------------------------------------------------------
# TransferRequest
# ---------------------------------------------------------------------------


def test_transfer_request_valid():
    pid = uuid.uuid4()
    w1, w2 = uuid.uuid4(), uuid.uuid4()
    req = TransferRequest(product_id=pid, from_warehouse_id=w1, to_warehouse_id=w2, quantity=10)
    assert req.quantity == 10
    assert req.notes is None


def test_transfer_request_with_notes():
    pid = uuid.uuid4()
    w1, w2 = uuid.uuid4(), uuid.uuid4()
    req = TransferRequest(
        product_id=pid,
        from_warehouse_id=w1,
        to_warehouse_id=w2,
        quantity=5,
        notes="urgent restock",
    )
    assert req.notes == "urgent restock"


def test_transfer_request_same_warehouse_raises():
    pid = uuid.uuid4()
    w = uuid.uuid4()
    with pytest.raises(ValidationError):
        TransferRequest(product_id=pid, from_warehouse_id=w, to_warehouse_id=w, quantity=5)


def test_transfer_request_zero_quantity_raises():
    pid = uuid.uuid4()
    w1, w2 = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(ValidationError):
        TransferRequest(product_id=pid, from_warehouse_id=w1, to_warehouse_id=w2, quantity=0)


def test_transfer_request_negative_quantity_raises():
    pid = uuid.uuid4()
    w1, w2 = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(ValidationError):
        TransferRequest(product_id=pid, from_warehouse_id=w1, to_warehouse_id=w2, quantity=-5)


# ---------------------------------------------------------------------------
# StockLevelResponse
# ---------------------------------------------------------------------------


def test_stock_level_response_from_orm():
    now = datetime.now(UTC)
    pid = uuid.uuid4()
    wid = uuid.uuid4()
    sid = uuid.uuid4()

    class FakeProduct:
        id = pid
        name = "Widget"
        sku = "WGT-001"

    class FakeWarehouse:
        id = wid
        name = "Main Warehouse"
        location = "NYC"

    class FakeStockLevel:
        id = sid
        product_id = pid
        warehouse_id = wid
        quantity = 50
        min_threshold = 10
        created_at = now
        updated_at = now
        product = FakeProduct()
        warehouse = FakeWarehouse()

    resp = StockLevelResponse.model_validate(FakeStockLevel())
    assert resp.id == sid
    assert resp.product_id == pid
    assert resp.warehouse_id == wid
    assert resp.quantity == 50
    assert resp.min_threshold == 10
    assert resp.product.name == "Widget"
    assert resp.product.sku == "WGT-001"
    assert resp.warehouse.name == "Main Warehouse"
    assert resp.warehouse.location == "NYC"


# ---------------------------------------------------------------------------
# TransferResponse
# ---------------------------------------------------------------------------


def test_transfer_response_from_dict():
    now = datetime.now(UTC)
    tid = uuid.uuid4()
    pid = uuid.uuid4()
    w1, w2 = uuid.uuid4(), uuid.uuid4()
    uid = uuid.uuid4()
    resp = TransferResponse(
        id=tid,
        product_id=pid,
        from_warehouse_id=w1,
        to_warehouse_id=w2,
        quantity=25,
        initiated_by=uid,
        notes="test transfer",
        created_at=now,
    )
    assert resp.id == tid
    assert resp.quantity == 25
    assert resp.notes == "test transfer"
    assert resp.initiated_by == uid


def test_transfer_response_notes_optional():
    now = datetime.now(UTC)
    resp = TransferResponse(
        id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        from_warehouse_id=uuid.uuid4(),
        to_warehouse_id=uuid.uuid4(),
        quantity=5,
        initiated_by=uuid.uuid4(),
        notes=None,
        created_at=now,
    )
    assert resp.notes is None


def test_transfer_response_from_orm():
    now = datetime.now(UTC)
    tid = uuid.uuid4()
    pid = uuid.uuid4()
    w1, w2 = uuid.uuid4(), uuid.uuid4()
    uid = uuid.uuid4()

    class FakeTransfer:
        id = tid
        product_id = pid
        from_warehouse_id = w1
        to_warehouse_id = w2
        quantity = 10
        initiated_by = uid
        notes = None
        created_at = now

    resp = TransferResponse.model_validate(FakeTransfer())
    assert resp.id == tid
    assert resp.quantity == 10


# ---------------------------------------------------------------------------
# ProductSummary and WarehouseSummary
# ---------------------------------------------------------------------------


def test_product_summary_from_orm():
    pid = uuid.uuid4()

    class FakeProduct:
        id = pid
        name = "Gadget"
        sku = "GDG-001"

    ps = ProductSummary.model_validate(FakeProduct())
    assert ps.id == pid
    assert ps.sku == "GDG-001"


def test_warehouse_summary_from_orm():
    wid = uuid.uuid4()

    class FakeWarehouse:
        id = wid
        name = "East"
        location = "Boston"

    ws = WarehouseSummary.model_validate(FakeWarehouse())
    assert ws.id == wid
    assert ws.location == "Boston"


# ---------------------------------------------------------------------------
# StockAlertResponse
# ---------------------------------------------------------------------------


def test_stock_alert_response():
    pid = uuid.uuid4()
    wid = uuid.uuid4()
    product = ProductSummary(id=pid, name="Low Widget", sku="LW-001")
    warehouse = WarehouseSummary(id=wid, name="Store", location="LA")
    alert = StockAlertResponse(
        product=product,
        warehouse=warehouse,
        quantity=3,
        min_threshold=10,
        deficit=7,
    )
    assert alert.deficit == 7
    assert alert.product.name == "Low Widget"
    assert alert.warehouse.name == "Store"
    assert alert.quantity == 3
    assert alert.min_threshold == 10
