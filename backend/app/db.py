import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .settings import settings
from .models.base import Base

# Auto-adjust SQLite path to /tmp if running in a serverless environment
# (Vercel / AWS Lambda) where the working directory is read-only.
database_url = settings.DATABASE_URL
if database_url.startswith("sqlite") and (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")):
    if "./dev.db" in database_url or database_url.endswith("/dev.db"):
        database_url = "sqlite+aiosqlite:////tmp/dev.db"

# Create async engine
connect_args = {}
if database_url.startswith("sqlite"):
    connect_args = {"timeout": 30.0}

engine = create_async_engine(
    database_url,
    echo=getattr(settings, "DEBUG", False),
    future=True,
    connect_args=connect_args,
)

# Delete stale test-only SQLite files (never touch dev.db)
if database_url.startswith("sqlite+aiosqlite://"):
    db_path = database_url.split("///")[-1]
    if db_path != "./dev.db" and not db_path.endswith("/dev.db") and os.path.isfile(db_path):
        os.remove(db_path)

# Session factory
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# Lazy table creation – guarantees tables exist before the first query,
# even in serverless cold-starts where the startup event may not fire.
_tables_created = False

async def ensure_tables():
    global _tables_created
    if not _tables_created:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True

async def get_db() -> AsyncSession:
    """FastAPI dependency that provides an async session."""
    await ensure_tables()
    async with AsyncSessionLocal() as session:
        yield session

# Eagerly create tables on import when possible (dev / test).
try:
    asyncio.get_event_loop().run_until_complete(ensure_tables())
except RuntimeError:
    pass  # event loop already running – tables will be created lazily
