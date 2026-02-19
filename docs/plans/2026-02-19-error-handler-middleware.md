# Error Handler Middleware Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create global FastAPI exception handlers that return consistent JSON error envelopes.

**Architecture:** Three handler functions (`http_exception_handler`, `validation_exception_handler`, `integrity_error_handler`, `unhandled_exception_handler`) registered on the FastAPI app. Reuse existing `ErrorResponse`/`ErrorCode`/`ErrorDetail` schemas from `src/schemas/common.py`.

**Tech Stack:** FastAPI exception handlers, SQLAlchemy IntegrityError, Python logging, Pydantic v2, httpx + pytest for tests.

---

### Task 1: Create `src/middleware/__init__.py`

**Files:**
- Create: `src/middleware/__init__.py`

Empty package init file.

---

### Task 2: Create `src/middleware/error_handler.py`

**Files:**
- Create: `src/middleware/error_handler.py`

Four async handler functions:
1. `http_exception_handler` — maps HTTP status codes to error codes (404→NOT_FOUND, 401→UNAUTHORIZED, etc.)
2. `validation_exception_handler` — 422 with `details: [{field, message}]`
3. `integrity_error_handler` — 409, detects unique constraint → ALREADY_EXISTS, others → CONFLICT
4. `unhandled_exception_handler` — logs traceback, returns 500 INTERNAL_ERROR (no stack trace in response)

---

### Task 3: Create `tests/test_error_handler.py`

**Files:**
- Create: `tests/test_error_handler.py`

Tests covering all handler paths and the error response format.

---
