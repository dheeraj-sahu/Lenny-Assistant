"""
tests/test_api_sessions.py

Integration tests for the /sessions endpoints.
Uses httpx.AsyncClient against the FastAPI test app with an in-memory SQLite DB.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import create_app
from persistence.database import init_db
from persistence.models import Base


# ── Test app setup ────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///./test_sessions.db"


@pytest_asyncio.fixture(scope="function")
async def test_client():
    """Create a fresh test DB and async HTTP client for each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Override the module-level engine with the test engine
    import persistence.database as db_module
    db_module._engine = engine
    db_module._session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_session(test_client: AsyncClient):
    """POST /api/v1/sessions should return 201 with a valid session object."""
    response = await test_client.post("/api/v1/sessions", json={})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["active_provider"] in ("ollama", "anthropic")
    assert data["title"] is None


@pytest.mark.asyncio
async def test_create_session_with_title(test_client: AsyncClient):
    """POST /api/v1/sessions with a title should set the title."""
    response = await test_client.post(
        "/api/v1/sessions", json={"title": "  My test session  "}
    )
    assert response.status_code == 201
    assert response.json()["title"] == "My test session"


@pytest.mark.asyncio
async def test_create_session_rejects_blank_title(test_client: AsyncClient):
    """POST /api/v1/sessions should reject titles containing only whitespace."""
    response = await test_client.post("/api/v1/sessions", json={"title": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_sessions_empty(test_client: AsyncClient):
    """GET /api/v1/sessions on a fresh DB should return empty list."""
    response = await test_client.get("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_sessions_after_create(test_client: AsyncClient):
    """Sessions should appear in the list after creation."""
    await test_client.post("/api/v1/sessions", json={})
    await test_client.post("/api/v1/sessions", json={"title": "Second"})

    response = await test_client.get("/api/v1/sessions")
    assert response.status_code == 200
    assert response.json()["total"] == 2


@pytest.mark.asyncio
async def test_list_sessions_rejects_invalid_pagination(test_client: AsyncClient):
    """GET /api/v1/sessions should reject invalid limit and offset values."""
    for query in ("?limit=0", "?limit=101", "?offset=-1"):
        response = await test_client.get(f"/api/v1/sessions{query}")
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_session_not_found(test_client: AsyncClient):
    """GET /api/v1/sessions/{unknown-id} should return 404."""
    fake_id = "00000000-0000-0000-0000-000000000001"
    response = await test_client.get(f"/api/v1/sessions/{fake_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_session_found(test_client: AsyncClient):
    """GET /api/v1/sessions/{id} should return the created session."""
    create_resp = await test_client.post("/api/v1/sessions", json={"title": "Found session"})
    session_id = create_resp.json()["id"]

    response = await test_client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["id"] == session_id
    assert response.json()["title"] == "Found session"


@pytest.mark.asyncio
async def test_delete_session(test_client: AsyncClient):
    """DELETE /api/v1/sessions/{id} should return 204 then 404 on second delete."""
    create_resp = await test_client.post("/api/v1/sessions", json={})
    session_id = create_resp.json()["id"]

    delete_resp = await test_client.delete(f"/api/v1/sessions/{session_id}")
    assert delete_resp.status_code == 204

    # Should now return 404
    get_resp = await test_client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient):
    """/health should return a dict with 'status' and 'components'."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]


@pytest.mark.asyncio
async def test_config_endpoint(test_client: AsyncClient):
    """/config should return provider and model info."""
    response = await test_client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "model" in data
    assert "provider_label" in data
