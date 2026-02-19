"""Tests for src/middleware/access_log.py.

Each behaviour is exercised through a minimal FastAPI test application that
wires both RequestIdMiddleware (outermost) and AccessLogMiddleware together,
matching the intended production configuration.
"""

import json
import logging
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.middleware.access_log import AccessLogMiddleware
from src.middleware.request_id import RequestIdMiddleware


# ---------------------------------------------------------------------------
# Test application factory
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Minimal app with both middlewares wired in production order.

    Middleware is added in reverse dependency order:
    - AccessLogMiddleware added first → runs innermost
    - RequestIdMiddleware added last  → runs outermost, sets ContextVar first
    """
    app = FastAPI()
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "true"}

    @app.get("/error")
    async def error_route() -> dict[str, str]:  # type: ignore[return]
        raise HTTPException(status_code=404, detail="Not found")

    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_make_app(), raise_server_exceptions=False)


def _get_access_log_record(caplog: pytest.LogCaptureFixture) -> dict[str, object]:
    """Return the first parsed JSON record emitted by the access log middleware."""
    records = [r for r in caplog.records if r.name == "src.middleware.access_log"]
    assert records, "No access log record found"
    return json.loads(records[0].message)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Log emission
# ---------------------------------------------------------------------------


class TestAccessLogEmission:
    def test_log_emitted_for_request(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        records = [r for r in caplog.records if r.name == "src.middleware.access_log"]
        assert len(records) >= 1

    def test_log_level_is_info(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        records = [r for r in caplog.records if r.name == "src.middleware.access_log"]
        assert all(r.levelno == logging.INFO for r in records)


# ---------------------------------------------------------------------------
# Log format
# ---------------------------------------------------------------------------


class TestAccessLogFormat:
    def test_log_is_valid_json(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert isinstance(record, dict)

    def test_log_contains_method_field(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert "method" in record

    def test_log_contains_path_field(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert "path" in record

    def test_log_contains_status_field(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert "status" in record

    def test_log_contains_duration_ms_field(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert "duration_ms" in record

    def test_log_contains_request_id_field(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert "request_id" in record


# ---------------------------------------------------------------------------
# Field values
# ---------------------------------------------------------------------------


class TestAccessLogValues:
    def test_method_matches_request(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert record["method"] == "GET"

    def test_path_matches_request(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert record["path"] == "/ping"

    def test_status_matches_200_response(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert record["status"] == 200

    def test_status_matches_non_200_response(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/error")
        record = _get_access_log_record(caplog)
        assert record["status"] == 404

    def test_duration_ms_is_numeric(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert isinstance(record["duration_ms"], (int, float))

    def test_duration_ms_is_non_negative(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        assert record["duration_ms"] >= 0  # type: ignore[operator]

    def test_request_id_is_valid_uuid(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            client.get("/ping")
        record = _get_access_log_record(caplog)
        # Should not raise — confirms RequestIdMiddleware context is visible
        uuid.UUID(str(record["request_id"]))

    def test_request_id_matches_response_header(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="src.middleware.access_log"):
            res = client.get("/ping")
        record = _get_access_log_record(caplog)
        assert record["request_id"] == res.headers["x-request-id"]
