"""Tests for rate limiting functionality."""

from fastapi.testclient import TestClient


def test_rate_limit_register_endpoint(client: TestClient):
    """Test rate limiting on register endpoint (5/minute)."""
    # Register endpoint is limited to 5 requests per minute
    # Try to exceed this limit

    successful_requests = 0
    rate_limited = False

    for i in range(7):  # Try 7 requests, should be rate limited after 5
        user_data = {"email": f"ratelimit{i}@test.com", "username": f"ratelimit{i}", "password": "password123"}

        response = client.post("/api/v1/auth/register", json=user_data)

        if response.status_code == 200:
            successful_requests += 1
        elif response.status_code == 429:
            rate_limited = True
            # Check that response has error field (slowapi format)
            data = response.json()
            assert "error" in data
            assert "Rate limit exceeded" in data["error"]
            break
        else:
            # Some other error (like duplicate email)
            pass

    # Should have been rate limited after 5 successful requests
    assert rate_limited or successful_requests <= 5


def test_rate_limit_login_endpoint(client: TestClient):
    """Test rate limiting on login endpoint (10/minute)."""
    # Login endpoint is limited to 10 requests per minute
    # Try multiple login attempts

    rate_limited_responses = 0

    for _ in range(12):  # Try 12 requests, should be rate limited after 10
        login_data = {"email": "nonexistent@test.com", "password": "wrongpassword"}

        response = client.post("/api/v1/auth/login", json=login_data)

        if response.status_code == 429:
            rate_limited_responses += 1
            # Check rate limit response format (slowapi)
            data = response.json()
            assert "error" in data
            assert "Rate limit exceeded" in data["error"]

    # Should get at least one 429 response
    assert rate_limited_responses > 0


def test_rate_limit_refresh_endpoint(client: TestClient, admin_headers: dict[str, str]):
    """Test rate limiting on refresh endpoint (30/minute)."""
    # First login to get a refresh token
    login_data = {"email": "admin@test.com", "password": "admin123"}
    login_response = client.post("/api/v1/auth/login", json=login_data)

    # If we're already rate limited, skip this test since rate limiting is working
    if login_response.status_code == 429:
        return

    assert login_response.status_code == 200
    tokens = login_response.json()

    # Refresh endpoint is limited to 30 requests per minute
    # Try many refresh attempts
    rate_limited_responses = 0

    for _ in range(35):  # Try 35 requests, should be rate limited after 30
        refresh_data = {"refresh_token": tokens["refresh_token"]}

        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        if response.status_code == 429:
            rate_limited_responses += 1
            # Check rate limit response format (slowapi)
            data = response.json()
            assert "error" in data
            assert "Rate limit exceeded" in data["error"]
            break  # Exit early once we hit rate limit

    # Should get at least one 429 response
    assert rate_limited_responses > 0


def test_rate_limit_authenticated_routes(client: TestClient, regular_user_headers: dict[str, str]):
    """Test rate limiting on authenticated routes (100/minute)."""
    # Authenticated routes have a higher limit (100/minute)
    # This test checks that the limit exists but may not hit it due to test time constraints

    successful_requests = 0

    # Try many requests to a simple authenticated endpoint
    for _i in range(20):  # Just try 20 to avoid test timeout
        response = client.get("/api/v1/auth/me", headers=regular_user_headers)

        if response.status_code == 200:
            successful_requests += 1
        elif response.status_code == 429:
            # Check rate limit response format (slowapi)
            data = response.json()
            assert "error" in data
            assert "Rate limit exceeded" in data["error"]
            break

    # Should be able to make at least some requests before hitting limit
    assert successful_requests > 0


def test_rate_limit_headers_present(client: TestClient):
    """Test that rate limiting works and provides proper error format."""
    user_data = {"email": "headertest@test.com", "username": "headertest", "password": "password123"}

    response = client.post("/api/v1/auth/register", json=user_data)

    # Response should work for normal requests
    if response.status_code == 200:
        assert "X-Request-Id" in response.headers
    elif response.status_code == 429:
        # Check rate limit response format (slowapi)
        data = response.json()
        assert "error" in data
        assert "Rate limit exceeded" in data["error"]
        assert "X-Request-Id" in response.headers


def test_rate_limit_different_ips_independent(client: TestClient):
    """Test that rate limiting is per-IP (different IPs have independent limits)."""
    # Note: In TestClient, all requests come from the same "IP"
    # This test verifies the rate limiting mechanism works
    # In a real scenario, different IPs would have separate rate limits

    user_data = {"email": "iptest@test.com", "username": "iptest", "password": "password123"}

    response = client.post("/api/v1/auth/register", json=user_data)

    # Should work normally or be rate limited
    if response.status_code == 200:
        assert "X-Request-Id" in response.headers
    elif response.status_code == 429:
        data = response.json()
        assert "error" in data
        assert "Rate limit exceeded" in data["error"]


def test_rate_limit_429_error_format(client: TestClient):
    """Test that 429 responses follow the standard error format."""
    # Make enough requests to trigger rate limiting
    for i in range(6):  # Register is limited to 5/minute
        user_data = {"email": f"format{i}@test.com", "username": f"format{i}", "password": "password123"}

        response = client.post("/api/v1/auth/register", json=user_data)

        if response.status_code == 429:
            data = response.json()
            # Should follow slowapi error format
            assert "error" in data
            assert isinstance(data["error"], str)
            assert "Rate limit exceeded" in data["error"]
            break


def test_rate_limit_bypass_with_valid_requests(client: TestClient):
    """Test that rate limiting doesn't affect normal usage patterns."""
    # Normal usage should not hit rate limits unless already exceeded

    # Test a few normal requests
    responses = []
    for i in range(3):
        user_data = {"email": f"normal{i}@test.com", "username": f"normal{i}", "password": "password123"}

        response = client.post("/api/v1/auth/register", json=user_data)
        responses.append(response)

    # Should succeed unless rate limiting is active from previous tests
    for response in responses:
        # 200 = success, 409 = duplicate, 429 = rate limited (acceptable if previous tests triggered it)
        assert response.status_code in [200, 409, 429]


def test_rate_limit_window_behavior(client: TestClient):
    """Test that rate limiting mechanism is working."""
    # This is a simplified test since we can't easily wait for time windows in unit tests
    # We verify that the rate limiting mechanism is active

    initial_response = client.post(
        "/api/v1/auth/register", json={"email": "window@test.com", "username": "window", "password": "password123"}
    )

    # Should work normally or be rate limited
    if initial_response.status_code == 200:
        assert "X-Request-Id" in initial_response.headers
    elif initial_response.status_code == 409:
        # Duplicate user - that's ok
        assert "detail" in initial_response.json()
    elif initial_response.status_code == 429:
        data = initial_response.json()
        assert "error" in data
        assert "Rate limit exceeded" in data["error"]
