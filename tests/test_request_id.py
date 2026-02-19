"""Tests for src/middleware/request_id.py.

Each behaviour is exercised through a minimal FastAPI test application so the
full request/response cycle (header attachment, UUID generation, ContextVar
availability) is verified.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.request_id import REQUEST_ID_CTX, RequestIdMiddleware

# ---------------------------------------------------------------------------
# Test application factory
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Return a minimal FastAPI app with RequestIdMiddleware registered."""
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        # Expose the ContextVar value so tests can assert it matches the header
        return {"request_id": REQUEST_ID_CTX.get()}

    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_make_app())


# ---------------------------------------------------------------------------
# Header presence and format
# ---------------------------------------------------------------------------


class TestRequestIdHeader:
    def test_response_has_x_request_id_header(self, client: TestClient) -> None:
        res = client.get("/ping")
        assert "x-request-id" in res.headers

    def test_request_id_is_valid_uuid4(self, client: TestClient) -> None:
        res = client.get("/ping")
        request_id = res.headers["x-request-id"]
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_different_requests_get_different_ids(self, client: TestClient) -> None:
        id1 = client.get("/ping").headers["x-request-id"]
        id2 = client.get("/ping").headers["x-request-id"]
        assert id1 != id2

    def test_header_present_on_any_path(self, client: TestClient) -> None:
        # Even on unknown paths (404), the header should be injected
        res = client.get("/does-not-exist")
        assert "x-request-id" in res.headers

    def test_request_id_is_non_empty_string(self, client: TestClient) -> None:
        res = client.get("/ping")
        assert len(res.headers["x-request-id"]) > 0


# ---------------------------------------------------------------------------
# ContextVar availability
# ---------------------------------------------------------------------------


class TestRequestIdContextVar:
    def test_context_var_matches_response_header(self, client: TestClient) -> None:
        """The ContextVar value seen by a route handler equals the response header."""
        res = client.get("/ping")
        header_id = res.headers["x-request-id"]
        body_id = res.json()["request_id"]
        assert body_id == header_id

    def test_context_var_contains_valid_uuid(self, client: TestClient) -> None:
        res = client.get("/ping")
        body_id = res.json()["request_id"]
        parsed = uuid.UUID(body_id)
        assert parsed.version == 4
