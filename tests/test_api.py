"""Integration tests for the API using mock AI mode + SQLite."""
import io
import os

os.environ.setdefault("AI_MOCK_MODE", "true")
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_vv.db")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import engine, init_db, Base
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login(client):
    payload = {"full_name": "Jane Speaker", "email": "jane@example.com", "password": "supersecret1"}
    res = await client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    token = res.json()["access_token"]
    assert token

    res = await client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert res.status_code == 200

    res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "jane@example.com"


@pytest.mark.asyncio
async def test_duplicate_register_rejected(client):
    payload = {"full_name": "A B", "email": "dup@example.com", "password": "supersecret1"}
    await client.post("/api/auth/register", json=payload)
    res = await client.post("/api/auth/register", json=payload)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_guest_flow_and_analysis(client):
    res = await client.post("/api/auth/guest")
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert res.json()["is_guest"] is True

    fake_audio = io.BytesIO(b"RIFFfake-wav-bytes-for-mock-mode-only")
    files = {"file": ("test.wav", fake_audio, "audio/wav")}
    res = await client.post("/api/analyses", files=files, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "done"
    assert data["fluency_score"] is not None
    assert data["report"]["ai_insights"]

    res = await client.get("/api/analyses", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client):
    res = await client.get("/api/analyses")
    assert res.status_code == 401
