"""CI helper: initialise SQLite test database schema before running pytest.

Run this BEFORE pytest so that all tables exist on a fresh runner.
The conftest.py autouse fixture is a belt-and-suspenders guard; this script
ensures the DB is ready before Python even begins collecting tests.
"""
import asyncio
import os

# Must set env vars before any app import to avoid importing with wrong DATABASE_URL.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///./test_dev.db")
os.environ.setdefault("USE_MOCK", "true")


async def init_db() -> None:
    # Import after env vars are set.
    from backend.app.db import engine, Base  # noqa: PLC0415

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Test database schema initialised successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
