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
