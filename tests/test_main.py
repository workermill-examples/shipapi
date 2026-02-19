from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_engine_connect():
    """Patch engine.connect so lifespan doesn't need a real DB."""
    with patch("src.main.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_engine.dispose = AsyncMock()
        yield mock_engine


@pytest.fixture
async def client(mock_engine_connect):
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_openapi_returns_200(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_app_title_and_version(client):
    response = await client.get("/openapi.json")
    data = response.json()
    assert data["info"]["title"] == "ShipAPI"
    assert data["info"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_openapi_has_all_seven_tags(client):
    response = await client.get("/openapi.json")
    tag_names = {t["name"] for t in response.json()["tags"]}
    expected = {"Health", "Auth", "Categories", "Products", "Warehouses", "Stock", "Audit"}
    assert tag_names == expected


@pytest.mark.asyncio
async def test_docs_endpoint_accessible(client):
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_redoc_endpoint_accessible(client):
    response = await client.get("/redoc")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cors_allow_origin_header(client):
    response = await client.options(
        "/openapi.json",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORS middleware echoes the requesting origin (or "*") when origins are allowed
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] in ("*", "http://example.com")


# ---------------------------------------------------------------------------
# Swagger UI — security scheme verification (Authorize button)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_has_bearer_auth_scheme(client):
    """BearerAuth security scheme must appear in the OpenAPI spec so Swagger UI
    renders the Bearer JWT option inside the Authorize button."""
    response = await client.get("/openapi.json")
    schemes = response.json().get("components", {}).get("securitySchemes", {})
    assert "BearerAuth" in schemes, f"BearerAuth missing from securitySchemes: {list(schemes)}"
    bearer = schemes["BearerAuth"]
    assert bearer["type"] == "http"
    assert bearer["scheme"] == "bearer"


@pytest.mark.asyncio
async def test_openapi_has_api_key_auth_scheme(client):
    """ApiKeyAuth security scheme must appear in the OpenAPI spec so Swagger UI
    renders the X-API-Key option inside the Authorize button."""
    response = await client.get("/openapi.json")
    schemes = response.json().get("components", {}).get("securitySchemes", {})
    assert "ApiKeyAuth" in schemes, f"ApiKeyAuth missing from securitySchemes: {list(schemes)}"
    api_key = schemes["ApiKeyAuth"]
    assert api_key["type"] == "apiKey"
    assert api_key["in"] == "header"
    assert api_key["name"] == "X-API-Key"


@pytest.mark.asyncio
async def test_protected_endpoints_declare_both_security_schemes(client):
    """Every endpoint that requires authentication must declare both BearerAuth
    and ApiKeyAuth in its security array so Swagger UI shows the correct lock
    icon and the Authorize button pre-selects both schemes."""
    response = await client.get("/openapi.json")
    schema = response.json()
    paths = schema.get("paths", {})

    # Collect all operations that require auth (they reference get_current_user)
    # by checking that their security field lists both schemes.
    auth_required_paths: list[str] = []
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            security: list[dict] | None = operation.get("security")
            if security is not None:
                auth_required_paths.append(f"{method.upper()} {path}")
                scheme_names = {name for entry in security for name in entry}
                assert "BearerAuth" in scheme_names, (
                    f"{method.upper()} {path}: BearerAuth missing from security {security}"
                )
                assert "ApiKeyAuth" in scheme_names, (
                    f"{method.upper()} {path}: ApiKeyAuth missing from security {security}"
                )

    # At least /api/v1/auth/me must require auth
    assert any("/auth/me" in p for p in auth_required_paths), (
        "Expected GET /api/v1/auth/me to declare security requirements"
    )
