import os
import ssl
import urllib.parse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from .settings import settings
from .models.base import Base

try:
    import certifi
    CA_FILE = certifi.where()
except ImportError:
    CA_FILE = None

# ---------------------------------------------------------------------------
# Configure database URL, connection args, and pool class
# ---------------------------------------------------------------------------
database_url = settings.DATABASE_URL
connect_args: dict = {}
pool_class = None  # let SQLAlchemy pick the default

if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
    # SQLAlchemy async requires the asyncpg driver prefix
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Strip query params that asyncpg doesn't understand
    parsed = urllib.parse.urlparse(database_url)
    qs = urllib.parse.parse_qs(parsed.query)
    clean_qs = {k: v for k, v in qs.items() if k not in ("sslmode", "channel_binding")}
    database_url = urllib.parse.urlunparse(
        parsed._replace(query=urllib.parse.urlencode(clean_qs, doseq=True))
    )

    # SSL for Neon / cloud PostgreSQL
    if CA_FILE:
        connect_args["ssl"] = ssl.create_default_context(cafile=CA_FILE)
    else:
        connect_args["ssl"] = True

    # NullPool is essential for serverless (Vercel / Lambda) — each invocation
    # gets a fresh connection; no stale connections across event loops.
    pool_class = NullPool

elif database_url.startswith("sqlite"):
    # Serverless read-only filesystem workaround
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        if "./dev.db" in database_url or database_url.endswith("/dev.db"):
            database_url = "sqlite+aiosqlite:////tmp/dev.db"
    connect_args["timeout"] = 30.0

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------
engine_kwargs: dict = dict(
    echo=getattr(settings, "DEBUG", False),
    future=True,
    connect_args=connect_args,
)
if pool_class is not None:
    engine_kwargs["poolclass"] = pool_class

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


# ---------------------------------------------------------------------------
# Lazy table creation — runs once per cold start via get_db() or startup event
# ---------------------------------------------------------------------------
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
