"""Tests for src/middleware/error_handler.py.

Each handler is exercised through a minimal FastAPI test application so the
full request/response cycle (serialisation, status codes, headers) is verified.
"""

import logging
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from src.middleware.error_handler import (
    http_exception_handler,
    integrity_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)

# ---------------------------------------------------------------------------
# Test application factory
# ---------------------------------------------------------------------------


class _Body(BaseModel):
    name: str
    count: int


def _make_app() -> FastAPI:
    """Return a minimal FastAPI app with all four handlers registered."""
    app = FastAPI()
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

    @app.get("/http/{code}")
    async def raise_http(code: int, msg: str = "error message") -> dict[str, str]:  # type: ignore[return]
        raise HTTPException(status_code=code, detail=msg)

    @app.post("/validate-body")
    async def validate_body(body: _Body) -> dict[str, object]:
        return {"name": body.name, "count": body.count}

    @app.get("/integrity/unique")
    async def raise_unique_integrity() -> dict[str, str]:  # type: ignore[return]
        orig = MagicMock()
        orig.__str__ = lambda self: "UNIQUE constraint failed: users.email"
        raise IntegrityError("stmt", {}, orig)

    @app.get("/integrity/other")
    async def raise_other_integrity() -> dict[str, str]:  # type: ignore[return]
        orig = MagicMock()
        orig.__str__ = lambda self: "FOREIGN KEY constraint failed"
        raise IntegrityError("stmt", {}, orig)

    @app.get("/crash")
    async def crash() -> dict[str, str]:  # type: ignore[return]
        raise RuntimeError("boom")

    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_make_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# HTTPException handler
# ---------------------------------------------------------------------------


class TestHttpExceptionHandler:
    def test_404_returns_not_found_code(self, client: TestClient) -> None:
        res = client.get("/http/404")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"

    def test_401_returns_unauthorized_code(self, client: TestClient) -> None:
        res = client.get("/http/401")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"

    def test_403_returns_forbidden_code(self, client: TestClient) -> None:
        res = client.get("/http/403")
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

    def test_400_returns_bad_request_code(self, client: TestClient) -> None:
        res = client.get("/http/400")
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "BAD_REQUEST"

    def test_409_returns_conflict_code(self, client: TestClient) -> None:
        res = client.get("/http/409")
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "CONFLICT"

    def test_detail_appears_as_message(self, client: TestClient) -> None:
        res = client.get("/http/404?msg=resource+not+here")
        assert res.json()["error"]["message"] == "resource not here"

    def test_unknown_status_uses_http_prefix(self, client: TestClient) -> None:
        res = client.get("/http/418")
        assert res.status_code == 418
        assert res.json()["error"]["code"] == "HTTP_418"

    def test_response_has_no_details_field(self, client: TestClient) -> None:
        res = client.get("/http/404")
        assert res.json()["error"]["details"] is None

    def test_envelope_has_error_key(self, client: TestClient) -> None:
        res = client.get("/http/404")
        body = res.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]


# ---------------------------------------------------------------------------
# Validation exception handler
# ---------------------------------------------------------------------------


class TestValidationExceptionHandler:
    def test_missing_required_field_returns_422(self, client: TestClient) -> None:
        # Send empty body → name and count are missing
        res = client.post("/validate-body", json={})
        assert res.status_code == 422

    def test_code_is_unprocessable_entity(self, client: TestClient) -> None:
        res = client.post("/validate-body", json={})
        assert res.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"

    def test_message_is_validation_failed(self, client: TestClient) -> None:
        res = client.post("/validate-body", json={})
        assert res.json()["error"]["message"] == "Request validation failed"

    def test_details_list_contains_field_errors(self, client: TestClient) -> None:
        res = client.post("/validate-body", json={})
        details = res.json()["error"]["details"]
        assert isinstance(details, list)
        assert len(details) >= 1

    def test_detail_entry_has_field_and_message(self, client: TestClient) -> None:
        res = client.post("/validate-body", json={})
        entry = res.json()["error"]["details"][0]
        assert "field" in entry
        assert "message" in entry

    def test_wrong_type_shows_field_name(self, client: TestClient) -> None:
        # count must be int; send string → validation error with field "count"
        res = client.post("/validate-body", json={"name": "widget", "count": "oops"})
        assert res.status_code == 422
        fields = [d["field"] for d in res.json()["error"]["details"]]
        assert any("count" in f for f in fields)

    def test_body_prefix_stripped_from_field(self, client: TestClient) -> None:
        # Pydantic loc includes "body" prefix; it should be stripped in output
        res = client.post("/validate-body", json={})
        fields = [d["field"] for d in res.json()["error"]["details"]]
        assert not any(f.startswith("body") for f in fields)


# ---------------------------------------------------------------------------
# IntegrityError handler
# ---------------------------------------------------------------------------


class TestIntegrityErrorHandler:
    def test_unique_constraint_returns_409(self, client: TestClient) -> None:
        res = client.get("/integrity/unique")
        assert res.status_code == 409

    def test_unique_constraint_code_is_already_exists(self, client: TestClient) -> None:
        res = client.get("/integrity/unique")
        assert res.json()["error"]["code"] == "ALREADY_EXISTS"

    def test_other_integrity_error_returns_409(self, client: TestClient) -> None:
        res = client.get("/integrity/other")
        assert res.status_code == 409

    def test_other_integrity_error_code_is_conflict(self, client: TestClient) -> None:
        res = client.get("/integrity/other")
        assert res.json()["error"]["code"] == "CONFLICT"

    def test_response_has_message(self, client: TestClient) -> None:
        res = client.get("/integrity/unique")
        assert res.json()["error"]["message"]


# ---------------------------------------------------------------------------
# Unhandled exception handler
# ---------------------------------------------------------------------------


class TestUnhandledExceptionHandler:
    def test_unhandled_exception_returns_500(self, client: TestClient) -> None:
        res = client.get("/crash")
        assert res.status_code == 500

    def test_code_is_internal_error(self, client: TestClient) -> None:
        res = client.get("/crash")
        assert res.json()["error"]["code"] == "INTERNAL_ERROR"

    def test_no_stack_trace_in_response(self, client: TestClient) -> None:
        res = client.get("/crash")
        body_str = res.text
        # Stack trace markers must not appear in the response body
        assert "Traceback" not in body_str
        assert "RuntimeError" not in body_str

    def test_generic_message_returned(self, client: TestClient) -> None:
        res = client.get("/crash")
        assert "internal server error" in res.json()["error"]["message"].lower()

    def test_traceback_logged(self, client: TestClient, caplog: pytest.LogCaptureFixture) -> None:

        with caplog.at_level(logging.ERROR, logger="src.middleware.error_handler"):
            client.get("/crash")
        # At least one ERROR log entry must have been emitted
        assert any(rec.levelname == "ERROR" for rec in caplog.records)
