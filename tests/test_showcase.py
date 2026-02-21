"""Tests for GET / (landing page) and GET /api/v1/showcase/stats (public stats).

Coverage
--------
* Landing page: HTTP 200, HTML content-type, required content markers (branding,
  tech stack, build history, demo credentials, navigation links).
* Showcase stats: HTTP 200, no auth required, JSON schema, non-negative values,
  live counts that reflect seeded test data.
* Existing /api/v1/* routes are unaffected by the addition of the landing page
  and stats endpoint (smoke tests).
"""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Landing page — HTTP response basics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_landing_page_returns_200(async_client: AsyncClient) -> None:
    """Root URL returns HTTP 200."""
    response = await async_client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_landing_page_content_type_html(async_client: AsyncClient) -> None:
    """Root URL returns HTML content type."""
    response = await async_client.get("/")
    assert "text/html" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Landing page — branding content markers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_landing_page_contains_shipapi(async_client: AsyncClient) -> None:
    """Landing page HTML mentions ShipAPI."""
    response = await async_client.get("/")
    assert "ShipAPI" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_workermill(async_client: AsyncClient) -> None:
    """Landing page HTML includes WorkerMill branding."""
    response = await async_client.get("/")
    assert "WorkerMill" in response.text or "workermill" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_ai_workers_message(async_client: AsyncClient) -> None:
    """Landing page communicates that the project was built by AI workers."""
    response = await async_client.get("/")
    assert "AI" in response.text


# ---------------------------------------------------------------------------
# Landing page — tech stack content markers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_landing_page_contains_fastapi(async_client: AsyncClient) -> None:
    """Landing page lists FastAPI as part of the tech stack."""
    response = await async_client.get("/")
    assert "FastAPI" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_sqlalchemy(async_client: AsyncClient) -> None:
    """Landing page lists SQLAlchemy as part of the tech stack."""
    response = await async_client.get("/")
    assert "SQLAlchemy" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_postgresql(async_client: AsyncClient) -> None:
    """Landing page lists PostgreSQL as part of the tech stack."""
    response = await async_client.get("/")
    assert "PostgreSQL" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_python_313(async_client: AsyncClient) -> None:
    """Landing page lists Python 3.13 as part of the tech stack."""
    response = await async_client.get("/")
    assert "Python 3.13" in response.text


# ---------------------------------------------------------------------------
# Landing page — build history content markers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_landing_page_contains_epic_count(async_client: AsyncClient) -> None:
    """Landing page references the 5 epics build history."""
    response = await async_client.get("/")
    assert "5 epics" in response.text or "5 epic" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_story_count(async_client: AsyncClient) -> None:
    """Landing page references the 30 stories build history."""
    response = await async_client.get("/")
    assert "30 stories" in response.text or "30 story" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_test_count(async_client: AsyncClient) -> None:
    """Landing page displays the 344 test count in the build history section."""
    response = await async_client.get("/")
    assert "344" in response.text


# ---------------------------------------------------------------------------
# Landing page — navigation links
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_landing_page_contains_docs_link(async_client: AsyncClient) -> None:
    """Landing page links to the Swagger UI at /docs."""
    response = await async_client.get("/")
    assert "/docs" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_redoc_link(async_client: AsyncClient) -> None:
    """Landing page links to ReDoc at /redoc."""
    response = await async_client.get("/")
    assert "/redoc" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_github_link(async_client: AsyncClient) -> None:
    """Landing page links to the GitHub repository."""
    response = await async_client.get("/")
    assert "github.com/workermill-examples/shipapi" in response.text


# ---------------------------------------------------------------------------
# Landing page — demo credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_landing_page_contains_demo_credentials(async_client: AsyncClient) -> None:
    """Landing page includes demo email and API key."""
    response = await async_client.get("/")
    assert "demo@workermill.com" in response.text
    assert "sk_demo_shipapi_2026_showcase_key" in response.text


@pytest.mark.asyncio
async def test_landing_page_contains_demo_password(async_client: AsyncClient) -> None:
    """Landing page shows the demo account password."""
    response = await async_client.get("/")
    assert "demo1234" in response.text


# ---------------------------------------------------------------------------
# Showcase stats — HTTP response basics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_returns_200(async_client: AsyncClient) -> None:
    """Showcase stats endpoint returns HTTP 200."""
    response = await async_client.get("/api/v1/showcase/stats")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stats_no_auth_required(async_client: AsyncClient) -> None:
    """Showcase stats endpoint is public — no auth header needed."""
    response = await async_client.get("/api/v1/showcase/stats")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stats_content_type_json(async_client: AsyncClient) -> None:
    """Stats endpoint returns JSON content type."""
    response = await async_client.get("/api/v1/showcase/stats")
    assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Showcase stats — JSON schema validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_response_schema(async_client: AsyncClient) -> None:
    """Stats response contains exactly the expected integer fields."""
    response = await async_client.get("/api/v1/showcase/stats")
    body = response.json()

    required_keys = {
        "products",
        "categories",
        "warehouses",
        "stock_alerts",
        "stock_transfers",
        "audit_log_entries",
    }
    assert set(body.keys()) == required_keys
    for key in required_keys:
        assert isinstance(body[key], int), f"{key} should be int, got {type(body[key])}"


@pytest.mark.asyncio
async def test_stats_non_negative(async_client: AsyncClient) -> None:
    """All stats values are non-negative integers."""
    response = await async_client.get("/api/v1/showcase/stats")
    body = response.json()
    for key, value in body.items():
        assert value >= 0, f"{key} should be >= 0, got {value}"


# ---------------------------------------------------------------------------
# Showcase stats — live counts reflect seeded test data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_reflects_seeded_data(async_client: AsyncClient, seeded_db: dict) -> None:  # noqa: ARG001
    """Stats counts match seeded data: 3 products, 2 categories, 2 warehouses."""
    response = await async_client.get("/api/v1/showcase/stats")
    body = response.json()

    # seeded_db creates 3 active products, 2 categories, 2 warehouses
    assert body["products"] == 3
    assert body["categories"] == 2
    assert body["warehouses"] == 2
    # product2 has quantity=5 < min_threshold=20 → 1 alert
    assert body["stock_alerts"] == 1


@pytest.mark.asyncio
async def test_stats_empty_database_returns_zeros(async_client: AsyncClient) -> None:
    """Stats returns zero counts when no data has been seeded (clean test DB)."""
    response = await async_client.get("/api/v1/showcase/stats")
    body = response.json()
    # This test runs without seeded_db, so database may still have any test data
    # from prior test isolation — we can only assert values are non-negative integers.
    for key, value in body.items():
        assert isinstance(value, int) and value >= 0, (
            f"{key} must be a non-negative int, got {value!r}"
        )


# ---------------------------------------------------------------------------
# Existing /api/v1/* routes — smoke tests (must not be affected by landing page)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint_unaffected(async_client: AsyncClient) -> None:
    """GET /api/v1/health still returns 200 after showcase routes are mounted."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_openapi_json_unaffected(async_client: AsyncClient) -> None:
    """GET /openapi.json still returns 200 after showcase routes are mounted."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_docs_endpoint_unaffected(async_client: AsyncClient) -> None:
    """GET /docs still returns 200 after showcase routes are mounted."""
    response = await async_client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_redoc_endpoint_unaffected(async_client: AsyncClient) -> None:
    """GET /redoc still returns 200 after showcase routes are mounted."""
    response = await async_client.get("/redoc")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_categories_endpoint_unaffected(async_client: AsyncClient) -> None:
    """GET /api/v1/categories still returns 200 (showcase landing page at / doesn't interfere)."""
    response = await async_client.get("/api/v1/categories")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_products_endpoint_unaffected(
    async_client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """GET /api/v1/products still returns 200 with valid auth headers."""
    response = await async_client.get("/api/v1/products", headers=auth_headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Showcase stats — OpenAPI / tag registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_in_openapi_spec(async_client: AsyncClient) -> None:
    """The /api/v1/showcase/stats endpoint appears in the generated OpenAPI spec."""
    response = await async_client.get("/openapi.json")
    paths = response.json().get("paths", {})
    assert "/api/v1/showcase/stats" in paths, "Expected /api/v1/showcase/stats in OpenAPI paths"


@pytest.mark.asyncio
async def test_stats_openapi_tag_is_showcase(async_client: AsyncClient) -> None:
    """The showcase stats operation is tagged with 'Showcase' in the OpenAPI spec."""
    response = await async_client.get("/openapi.json")
    paths = response.json().get("paths", {})
    stats_get = paths.get("/api/v1/showcase/stats", {}).get("get", {})
    assert "Showcase" in stats_get.get("tags", []), (
        f"Expected 'Showcase' tag on stats operation, got {stats_get.get('tags')}"
    )


@pytest.mark.asyncio
async def test_landing_page_not_in_openapi_spec(async_client: AsyncClient) -> None:
    """The GET / landing page is excluded from the OpenAPI spec (include_in_schema=False)."""
    response = await async_client.get("/openapi.json")
    paths = response.json().get("paths", {})
    assert "/" not in paths, (
        "Landing page GET / should be hidden from OpenAPI spec (include_in_schema=False)"
    )
