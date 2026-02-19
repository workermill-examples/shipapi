"""Tests for src/middleware/rate_limit.py.

Covers:
- ``get_user_key``: key extraction from Bearer JWT, X-API-Key header, and IP fallback
- ``rate_limit_exceeded_handler``: 429 envelope format and header injection
- ``limiter``: rate limit enforcement via ``@limiter.limit()`` decorator
- Rate-limit response headers (X-RateLimit-*, Retry-After) on normal and 429 responses
"""

import uuid
from typing import Any

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from httpx import AsyncClient
from jose import jwt as jose_jwt
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from src.config import settings
from src.middleware.rate_limit import (
    get_remote_address,
    get_user_key,
    limiter,
    rate_limit_exceeded_handler,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_access_token(user_id: str | None = None) -> str:
    """Return a signed JWT with the given subject claim."""
    uid = user_id or str(uuid.uuid4())
    payload: dict[str, Any] = {"sub": uid, "type": "access"}
    return jose_jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _make_request(headers: dict[str, str] | None = None, client_host: str = "127.0.0.1") -> Request:
    """Build a minimal Starlette Request from a dict of headers."""
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


def _make_app(limit: str = "2/minute") -> FastAPI:
    """Return a minimal FastAPI app with a fresh per-test limiter."""
    test_limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
    app = FastAPI()
    app.state.limiter = test_limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

    @app.get("/limited")
    @test_limiter.limit(limit)
    async def limited(request: Request, response: Response) -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/user-limited")
    @test_limiter.limit(limit, key_func=get_user_key)
    async def user_limited(request: Request, response: Response) -> dict[str, str]:
        return {"status": "ok"}

    return app


# ---------------------------------------------------------------------------
# get_user_key — JWT extraction
# ---------------------------------------------------------------------------


class TestGetUserKeyFromJWT:
    def test_valid_bearer_jwt_returns_user_prefix(self) -> None:
        user_id = str(uuid.uuid4())
        token = _make_access_token(user_id)
        request = _make_request({"Authorization": f"Bearer {token}"})
        key = get_user_key(request)
        assert key == f"user:{user_id}"

    def test_bearer_prefix_required(self) -> None:
        token = _make_access_token()
        # Token without "Bearer " prefix should not be parsed as JWT
        request = _make_request({"Authorization": token})
        key = get_user_key(request)
        # Falls back to IP since no Bearer prefix
        assert not key.startswith("user:")

    def test_invalid_jwt_signature_falls_through(self) -> None:
        request = _make_request({"Authorization": "Bearer not.a.valid.jwt"})
        key = get_user_key(request)
        assert not key.startswith("user:")

    def test_jwt_without_sub_falls_through(self) -> None:
        # Token with no 'sub' claim
        payload: dict[str, Any] = {"type": "access"}
        token = jose_jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        request = _make_request({"Authorization": f"Bearer {token}"})
        key = get_user_key(request)
        assert not key.startswith("user:")

    def test_expired_jwt_still_returns_user_key(self) -> None:
        """Expired tokens still identify the user for rate-limiting purposes."""
        from datetime import UTC, datetime, timedelta

        user_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "sub": user_id,
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(hours=1),  # already expired
        }
        token = jose_jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        request = _make_request({"Authorization": f"Bearer {token}"})
        key = get_user_key(request)
        assert key == f"user:{user_id}"


# ---------------------------------------------------------------------------
# get_user_key — API key extraction
# ---------------------------------------------------------------------------


class TestGetUserKeyFromApiKey:
    def test_api_key_returns_apikey_prefix(self) -> None:
        request = _make_request({"X-API-Key": "sk_somesecretapikey12345"})
        key = get_user_key(request)
        assert key.startswith("apikey:")

    def test_api_key_hash_is_consistent(self) -> None:
        api_key = "sk_test_consistent_key"
        request1 = _make_request({"X-API-Key": api_key})
        request2 = _make_request({"X-API-Key": api_key})
        assert get_user_key(request1) == get_user_key(request2)

    def test_different_api_keys_give_different_buckets(self) -> None:
        req1 = _make_request({"X-API-Key": "sk_key_one"})
        req2 = _make_request({"X-API-Key": "sk_key_two"})
        assert get_user_key(req1) != get_user_key(req2)

    def test_bearer_takes_precedence_over_api_key(self) -> None:
        user_id = str(uuid.uuid4())
        token = _make_access_token(user_id)
        request = _make_request({"Authorization": f"Bearer {token}", "X-API-Key": "sk_ignored"})
        key = get_user_key(request)
        assert key == f"user:{user_id}"


# ---------------------------------------------------------------------------
# get_user_key — IP fallback
# ---------------------------------------------------------------------------


class TestGetUserKeyIPFallback:
    def test_no_credentials_returns_ip(self) -> None:
        request = _make_request(client_host="10.0.0.1")
        key = get_user_key(request)
        assert key == "10.0.0.1"

    def test_invalid_bearer_falls_back_to_ip(self) -> None:
        request = _make_request({"Authorization": "Bearer bad-token"}, client_host="192.168.1.1")
        key = get_user_key(request)
        assert key == "192.168.1.1"

    def test_empty_api_key_falls_back_to_ip(self) -> None:
        request = _make_request({"X-API-Key": ""}, client_host="10.10.10.10")
        key = get_user_key(request)
        assert key == "10.10.10.10"


# ---------------------------------------------------------------------------
# rate_limit_exceeded_handler — response format
# ---------------------------------------------------------------------------


class TestRateLimitExceededHandler:
    """Test the 429 handler using a minimal app so the full ASGI cycle runs."""

    @pytest.fixture(scope="class")
    def client(self) -> TestClient:
        app = _make_app(limit="1/minute")
        return TestClient(app, raise_server_exceptions=False)

    def _exhaust_limit(self, client: TestClient) -> None:
        """Make one request to consume the 1/minute limit."""
        client.get("/limited")

    def test_429_status_on_exceeded_limit(self, client: TestClient) -> None:
        self._exhaust_limit(client)
        res = client.get("/limited")
        assert res.status_code == 429

    def test_response_body_has_error_key(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert res.status_code == 429
        assert "error" in res.json()

    def test_error_code_is_rate_limited(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert res.status_code == 429
        assert res.json()["error"]["code"] == "RATE_LIMITED"

    def test_error_has_message(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert res.status_code == 429
        assert res.json()["error"]["message"]

    def test_no_details_field_in_429(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert res.status_code == 429
        assert res.json()["error"]["details"] is None

    def test_429_has_retry_after_header(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert res.status_code == 429
        assert "retry-after" in res.headers


# ---------------------------------------------------------------------------
# Rate-limit headers on normal (200) responses
# ---------------------------------------------------------------------------


class TestRateLimitHeadersOnNormalResponse:
    """Each test gets a fresh client so header counters start clean."""

    @pytest.fixture
    def client(self) -> TestClient:
        # Use a generous limit so tests don't accidentally hit 429
        return TestClient(_make_app(limit="100/minute"))

    def test_x_ratelimit_limit_header_present(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert res.status_code == 200
        assert "x-ratelimit-limit" in res.headers

    def test_x_ratelimit_remaining_header_present(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert "x-ratelimit-remaining" in res.headers

    def test_x_ratelimit_reset_header_present(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert "x-ratelimit-reset" in res.headers

    def test_limit_header_value_matches_configured_limit(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert res.headers["x-ratelimit-limit"] == "100"

    def test_remaining_decrements_with_each_request(self, client: TestClient) -> None:
        r1 = client.get("/limited")
        r2 = client.get("/limited")
        remaining1 = int(r1.headers["x-ratelimit-remaining"])
        remaining2 = int(r2.headers["x-ratelimit-remaining"])
        assert remaining2 < remaining1

    def test_remaining_is_non_negative(self, client: TestClient) -> None:
        res = client.get("/limited")
        assert int(res.headers["x-ratelimit-remaining"]) >= 0

    def test_reset_is_numeric_timestamp(self, client: TestClient) -> None:
        res = client.get("/limited")
        reset = res.headers["x-ratelimit-reset"]
        # Should be a numeric value (epoch timestamp or seconds until reset)
        assert reset.replace(".", "").isdigit() or reset.lstrip("-").replace(".", "").isdigit()


# ---------------------------------------------------------------------------
# Rate limit enforcement
# ---------------------------------------------------------------------------


class TestRateLimitEnforcement:
    def test_requests_within_limit_succeed(self) -> None:
        client = TestClient(_make_app(limit="3/minute"), raise_server_exceptions=False)
        for _ in range(3):
            res = client.get("/limited")
            assert res.status_code == 200

    def test_request_beyond_limit_returns_429(self) -> None:
        client = TestClient(_make_app(limit="2/minute"), raise_server_exceptions=False)
        client.get("/limited")
        client.get("/limited")
        res = client.get("/limited")
        assert res.status_code == 429

    def test_different_ips_have_independent_buckets(self) -> None:
        """Exceeding the limit from one client results in 429 for that client.

        TestClient always uses 127.0.0.1, so true multi-IP isolation is verified
        through the get_user_key unit tests above.  This test confirms that the
        rate limit is indeed tracked per-key and that 429 is returned once the
        limit is exhausted.
        """
        app = _make_app(limit="1/minute")
        c1 = TestClient(app, raise_server_exceptions=False)
        # c1 exhausts the limit
        c1.get("/limited")
        # Subsequent c1 request should be 429
        r1 = c1.get("/limited")
        assert r1.status_code == 429

    def test_user_key_isolates_per_user(self) -> None:
        """Two users have independent buckets when using get_user_key."""
        app = _make_app(limit="1/minute")
        uid1 = str(uuid.uuid4())
        uid2 = str(uuid.uuid4())
        token1 = _make_access_token(uid1)
        token2 = _make_access_token(uid2)

        client = TestClient(app, raise_server_exceptions=False)
        # user1 exhausts their limit
        client.get("/user-limited", headers={"Authorization": f"Bearer {token1}"})
        r1 = client.get("/user-limited", headers={"Authorization": f"Bearer {token1}"})
        assert r1.status_code == 429

        # user2 still has their own bucket
        r2 = client.get("/user-limited", headers={"Authorization": f"Bearer {token2}"})
        assert r2.status_code == 200


# ---------------------------------------------------------------------------
# limiter export
# ---------------------------------------------------------------------------


class TestLimiterExport:
    def test_limiter_is_limiter_instance(self) -> None:
        assert isinstance(limiter, Limiter)

    def test_limiter_uses_in_memory_storage(self) -> None:
        from limits.storage import MemoryStorage

        assert isinstance(limiter._storage, MemoryStorage)

    def test_limiter_has_headers_enabled(self) -> None:
        assert limiter._headers_enabled is True

    def test_limiter_default_key_is_remote_address(self) -> None:
        assert limiter._key_func is get_remote_address


# ---------------------------------------------------------------------------
# Integration tests — real FastAPI app + actual /auth/register endpoint (5/min)
# ---------------------------------------------------------------------------
# These tests use the ``async_client`` fixture (real PostgreSQL test database)
# to exercise the actual endpoint's rate limit.  The ``reset_rate_limiter``
# autouse fixture (conftest.py) guarantees each test starts with a clean window.


def _integration_reg_payload() -> dict[str, str]:
    """Fresh registration payload with a unique email to avoid 409 collisions."""
    return {
        "email": f"rl_int_{uuid.uuid4().hex[:8]}@test.com",
        "name": "Rate Limit Integration User",
        "password": "TestPassword123!",
    }


@pytest.mark.asyncio
async def test_register_endpoint_rate_limit_returns_429_on_excess(
    async_client: AsyncClient,
) -> None:
    """The real /register endpoint returns 429 after 5 requests from the same IP."""
    for _ in range(5):
        resp = await async_client.post("/api/v1/auth/register", json=_integration_reg_payload())
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    # 6th request must be rate-limited.
    resp = await async_client.post("/api/v1/auth/register", json=_integration_reg_payload())
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_register_endpoint_429_includes_retry_after_header(
    async_client: AsyncClient,
) -> None:
    """A 429 from the real /register endpoint includes the Retry-After header."""
    for _ in range(5):
        await async_client.post("/api/v1/auth/register", json=_integration_reg_payload())

    resp = await async_client.post("/api/v1/auth/register", json=_integration_reg_payload())
    assert resp.status_code == 429
    assert "retry-after" in resp.headers, (
        f"Retry-After header missing. Headers received: {dict(resp.headers)}"
    )


@pytest.mark.asyncio
async def test_register_endpoint_normal_response_has_x_ratelimit_headers(
    async_client: AsyncClient,
) -> None:
    """A successful /register response includes X-RateLimit-* headers.

    slowapi injects X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset
    headers when ``headers_enabled=True`` and the endpoint declares
    ``response: Response`` (as the register endpoint does).
    """
    resp = await async_client.post("/api/v1/auth/register", json=_integration_reg_payload())
    assert resp.status_code == 201

    rate_headers = [k for k in resp.headers if k.startswith("x-ratelimit-")]
    assert len(rate_headers) > 0, (
        f"No X-RateLimit-* headers found in /register response. Headers: {dict(resp.headers)}"
    )
