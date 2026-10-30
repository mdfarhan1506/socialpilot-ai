import os
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .settings import settings

# Create async engine using configured DATABASE_URL
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"timeout": 30.0}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=getattr(settings, "DEBUG", False),
    future=True,
    connect_args=connect_args,
)

# Ensure a fresh SQLite file for test databases (avoid wiping prod dev.db)
if settings.DATABASE_URL.startswith("sqlite+aiosqlite://"):
    db_path = settings.DATABASE_URL.split("///")[-1]
    # Only delete if it's not the default development DB
    if db_path != "./dev.db" and os.path.isfile(db_path):
        os.remove(db_path)

# Session factory for FastAPI dependencies
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

async def get_db() -> AsyncSession:
    """FastAPI dependency that provides an async session."""
    async with AsyncSessionLocal() as session:
        yield session

# Create tables automatically on import for both dev and test environments
import asyncio
from .models.base import Base

async def _create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

try:
    asyncio.get_event_loop().run_until_complete(_create_all_tables())
except RuntimeError:
    # Event loop already running (e.g., when using an async framework)
    asyncio.create_task(_create_all_tables())
