"""Shared test helpers – importable as both a package module and standalone."""
import os

# Set env vars BEFORE any app import.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")

from fastapi.testclient import TestClient  # noqa: E402
import pytest                              # noqa: E402
import asyncio                             # noqa: E402
from backend.app.main import app           # noqa: E402
from backend.app.db import engine, Base    # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Ensure all database tables exist before running any tests on clean DBs."""
    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_init())


def get_auth_headers(email: str, password: str = "testpass123") -> dict:
    """Register (if new) and login, return Authorization headers."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def create_workspace(headers: dict, name: str = "Test WS") -> str:
    resp = client.post("/workspace/", json={"name": name}, headers=headers)
    assert resp.status_code == 200, f"Workspace creation failed: {resp.text}"
    return resp.json()["id"]
