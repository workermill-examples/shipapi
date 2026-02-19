# Warehouse & Stock Pydantic Schemas Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Pydantic v2 request/response schemas for warehouse and stock management endpoints.

**Architecture:** Three pure schema files — warehouse.py and stock.py hold domain models, __init__.py re-exports everything. Schemas use `ConfigDict(from_attributes=True)` for ORM compatibility. Embedded sub-schemas (ProductSummary, WarehouseSummary) avoid circular imports.

**Tech Stack:** Pydantic v2 (`BaseModel`, `ConfigDict`, `field_validator`, `model_validator`), Python 3.13 type syntax (`X | Y` unions), UUID from stdlib.

---

### Task 1: Warehouse Schemas (`src/schemas/warehouse.py`)

**Files:**
- Create: `src/schemas/warehouse.py`
- Test: `tests/test_schemas_warehouse.py`

**Step 1: Write the failing tests**

```python
# tests/test_schemas_warehouse.py
import uuid
from datetime import datetime, timezone

import pytest

from src.schemas.warehouse import (
    WarehouseCreate,
    WarehouseDetailResponse,
    WarehouseResponse,
    WarehouseUpdate,
)


def test_warehouse_create_valid():
    w = WarehouseCreate(name="Main", location="NYC", capacity=500)
    assert w.name == "Main"
    assert w.capacity == 500


def test_warehouse_create_strips_whitespace():
    w = WarehouseCreate(name="  Main  ", location="  NYC  ", capacity=100)
    assert w.name == "Main"
    assert w.location == "NYC"


def test_warehouse_create_empty_name_raises():
    with pytest.raises(Exception):
        WarehouseCreate(name="   ", location="NYC", capacity=100)


def test_warehouse_create_zero_capacity_raises():
    with pytest.raises(Exception):
        WarehouseCreate(name="A", location="NYC", capacity=0)


def test_warehouse_create_negative_capacity_raises():
    with pytest.raises(Exception):
        WarehouseCreate(name="A", location="NYC", capacity=-1)


def test_warehouse_update_all_optional():
    u = WarehouseUpdate()
    assert u.name is None
    assert u.location is None
    assert u.capacity is None
    assert u.is_active is None


def test_warehouse_update_partial():
    u = WarehouseUpdate(name="New Name")
    assert u.name == "New Name"
    assert u.capacity is None


def test_warehouse_response_from_orm():
    now = datetime.now(timezone.utc)
    wid = uuid.uuid4()
    # Simulate ORM object with attribute access
    class FakeWarehouse:
        id = wid
        name = "Test"
        location = "NYC"
        capacity = 100
        is_active = True
        created_at = now
        updated_at = now

    resp = WarehouseResponse.model_validate(FakeWarehouse())
    assert resp.id == wid
    assert resp.name == "Test"


def test_warehouse_detail_response_has_stock_summary():
    now = datetime.now(timezone.utc)
    wid = uuid.uuid4()

    class FakeWarehouse:
        id = wid
        name = "Detail"
        location = "LA"
        capacity = 200
        is_active = True
        created_at = now
        updated_at = now

    detail = WarehouseDetailResponse.model_validate(
        FakeWarehouse(),
        update={"total_products": 5, "total_quantity": 120, "capacity_utilization_pct": 60.0},
    )
    assert detail.total_products == 5
    assert detail.total_quantity == 120
    assert detail.capacity_utilization_pct == 60.0
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_schemas_warehouse.py -v
```
Expected: FAIL (ImportError — module doesn't exist yet)

**Step 3: Implement `src/schemas/warehouse.py`**

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class WarehouseCreate(BaseModel):
    name: str
    location: str
    capacity: int

    @field_validator("name", "location")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be empty")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Capacity must be greater than 0")
        return v


class WarehouseUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    capacity: int | None = None
    is_active: bool | None = None

    @field_validator("name", "location")
    @classmethod
    def strip_and_require(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Field must not be empty")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Capacity must be greater than 0")
        return v


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    location: str
    capacity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WarehouseDetailResponse(WarehouseResponse):
    total_products: int
    total_quantity: int
    capacity_utilization_pct: float
```

**Step 4: Run tests to verify pass**

```bash
pytest tests/test_schemas_warehouse.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/schemas/warehouse.py tests/test_schemas_warehouse.py
git commit -m "feat: add warehouse Pydantic schemas"
```

---

### Task 2: Stock Schemas (`src/schemas/stock.py`)

**Files:**
- Create: `src/schemas/stock.py`
- Test: `tests/test_schemas_stock.py`

**Step 1: Write the failing tests**

```python
# tests/test_schemas_stock.py
import uuid
from datetime import datetime, timezone

import pytest

from src.schemas.stock import (
    ProductSummary,
    StockAlertResponse,
    StockLevelResponse,
    StockUpdateRequest,
    TransferRequest,
    TransferResponse,
    WarehouseSummary,
)


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
    with pytest.raises(Exception):
        StockUpdateRequest(quantity=-1)


def test_stock_update_request_negative_threshold_raises():
    with pytest.raises(Exception):
        StockUpdateRequest(quantity=5, min_threshold=-1)


def test_transfer_request_valid():
    pid = uuid.uuid4()
    w1 = uuid.uuid4()
    w2 = uuid.uuid4()
    req = TransferRequest(product_id=pid, from_warehouse_id=w1, to_warehouse_id=w2, quantity=10)
    assert req.quantity == 10
    assert req.notes is None


def test_transfer_request_same_warehouse_raises():
    pid = uuid.uuid4()
    w = uuid.uuid4()
    with pytest.raises(Exception):
        TransferRequest(product_id=pid, from_warehouse_id=w, to_warehouse_id=w, quantity=5)


def test_transfer_request_zero_quantity_raises():
    pid = uuid.uuid4()
    w1, w2 = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(Exception):
        TransferRequest(product_id=pid, from_warehouse_id=w1, to_warehouse_id=w2, quantity=0)


def test_stock_level_response_from_orm():
    now = datetime.now(timezone.utc)
    pid = uuid.uuid4()
    wid = uuid.uuid4()
    sid = uuid.uuid4()

    class FakeProduct:
        id = pid
        name = "Widget"
        sku = "WGT-001"

    class FakeWarehouse:
        id = wid
        name = "Main"
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
    assert resp.quantity == 50
    assert resp.product.sku == "WGT-001"
    assert resp.warehouse.name == "Main"


def test_transfer_response_from_dict():
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid.uuid4(),
        "product_id": uuid.uuid4(),
        "from_warehouse_id": uuid.uuid4(),
        "to_warehouse_id": uuid.uuid4(),
        "quantity": 25,
        "initiated_by": uuid.uuid4(),
        "notes": "test transfer",
        "created_at": now,
    }
    resp = TransferResponse(**data)
    assert resp.quantity == 25
    assert resp.notes == "test transfer"


def test_stock_alert_response():
    pid = uuid.uuid4()
    wid = uuid.uuid4()
    product = ProductSummary(id=pid, name="Low Widget", sku="LW-001")
    warehouse = WarehouseSummary(id=wid, name="Store", location="LA")
    alert = StockAlertResponse(
        product=product, warehouse=warehouse, quantity=3, min_threshold=10, deficit=7
    )
    assert alert.deficit == 7
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_schemas_stock.py -v
```
Expected: FAIL (ImportError)

**Step 3: Implement `src/schemas/stock.py`**

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sku: str


class WarehouseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    location: str


class StockUpdateRequest(BaseModel):
    quantity: int
    min_threshold: int | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity must be >= 0")
        return v

    @field_validator("min_threshold")
    @classmethod
    def threshold_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("min_threshold must be >= 0")
        return v


class StockLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    warehouse_id: UUID
    product: ProductSummary
    warehouse: WarehouseSummary
    quantity: int
    min_threshold: int
    created_at: datetime
    updated_at: datetime


class TransferRequest(BaseModel):
    product_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: int
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Transfer quantity must be > 0")
        return v

    @model_validator(mode="after")
    def different_warehouses(self) -> "TransferRequest":
        if self.from_warehouse_id == self.to_warehouse_id:
            raise ValueError("from_warehouse_id and to_warehouse_id must be different")
        return self


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    quantity: int
    initiated_by: UUID
    notes: str | None
    created_at: datetime


class StockAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductSummary
    warehouse: WarehouseSummary
    quantity: int
    min_threshold: int
    deficit: int
```

**Step 4: Run tests to verify pass**

```bash
pytest tests/test_schemas_stock.py -v
```

**Step 5: Commit**

```bash
git add src/schemas/stock.py tests/test_schemas_stock.py
git commit -m "feat: add stock Pydantic schemas"
```

---

### Task 3: Update `src/schemas/__init__.py`

**Files:**
- Modify: `src/schemas/__init__.py`

**Step 1: Update the file** to add imports from warehouse and stock modules.

**Step 2: Run full test suite**

```bash
pytest -v
```

**Step 3: Run lint and typecheck**

```bash
ruff check . && mypy src
```

**Step 4: Commit**

```bash
git add src/schemas/__init__.py
git commit -m "feat: re-export warehouse and stock schemas from schemas package"
```
