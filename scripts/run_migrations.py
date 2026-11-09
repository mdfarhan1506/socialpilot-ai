#!/usr/bin/env python3
"""Pre-deploy migration runner.

Runs `alembic upgrade head` before the backend starts, so schema drift
(e.g. missing columns) cannot cause runtime ProgrammingError in production.

Usage (Vercel build command or any CI step):
    python3 scripts/run_migrations.py

Environment variables required:
    SYNC_DATABASE_URL  — synchronous SQLAlchemy URL for Alembic
                         e.g. postgresql://user:pass@host/db
                         (do NOT use the async +asyncpg prefix here)

The script exits non-zero on any error so the deployment is aborted before
the new code starts serving traffic against an out-of-date schema.
"""
import subprocess
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    db_url = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: SYNC_DATABASE_URL (or DATABASE_URL) is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"[pre-deploy] Running alembic upgrade head …")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=str(REPO_ROOT),
        env={**os.environ, "SYNC_DATABASE_URL": db_url},
    )
    if result.returncode != 0:
        print("[pre-deploy] ❌ Migration failed — aborting deployment.", file=sys.stderr)
        sys.exit(result.returncode)

    print("[pre-deploy] ✅ Schema is up to date.")


if __name__ == "__main__":
    main()
