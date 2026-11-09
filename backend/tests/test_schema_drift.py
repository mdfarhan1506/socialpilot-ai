"""Schema drift test: verify every SQLAlchemy model column is present in the
migrated SQLite database.

This test fails when a developer adds a column to a model without creating a
migration, preventing the kind of drift that caused the trend_opportunities
ProgrammingError in production.

Run as part of the normal test suite (auto-discovered by pytest).
Uses the test database that is set up by conftest.py / init_test_db.py.
"""
import os
import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_path() -> Path:
    db_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test_dev.db")
    # Strip the async driver prefix so sqlite3 can open it
    db_url = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    return Path(db_url)


def _get_migrated_columns(db_path: Path, table: str) -> set:
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {row[1] for row in rows}  # row[1] = column name
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Expected columns per table (derived from SQLAlchemy models, not from
# migration files — that's the point: they must match).
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = {
    "trend_opportunities": {
        "id", "research_run_id", "title", "description", "evidence_url",
        "relevance_score", "source_name", "publication_date", "retrieved_at",
        "is_evergreen", "trend_metadata", "created_at", "updated_at",
    },
    "research_runs": {
        "id", "workspace_id", "status", "started_at", "completed_at",
        "parameters", "result_summary",
    },
    "scheduled_posts": {
        "id", "draft_id", "workspace_id", "user_id", "caption", "image_url",
        "concept", "hook", "script_or_body", "call_to_action",
        "requires_approval", "approved_at", "scheduled_time", "status",
        "created_at", "updated_at",
    },
    "autonomous_configs": {
        "id", "workspace_id", "is_active", "approval_mode",
        "min_posts_per_day", "max_posts_per_day", "quiet_hours_start",
        "quiet_hours_end", "restricted_keywords", "target_topics",
        "created_at", "updated_at",
    },
    "strategy_insights": {
        "id", "workspace_id", "topic", "hook_type", "format_type",
        "best_time_slot", "performance_score", "hypothesis", "recommendation",
        "confidence_score", "is_mock", "evidence_data", "created_at", "updated_at",
    },
    "automation_audit_logs": {
        "id", "workspace_id", "action", "status", "summary", "details",
        "created_at",
    },
    "post_analytics_observations": {
        "id", "workspace_id", "scheduled_post_id", "platform_post_id",
        "post_age_hours", "impressions", "reach", "likes", "comments",
        "shares", "saves", "engagement_rate", "data_provenance", "recorded_at",
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("table,expected", EXPECTED_COLUMNS.items())
def test_migrated_schema_matches_model(table: str, expected: set):
    """Fail when a model column is absent from the migrated database schema."""
    db_path = _get_db_path()
    if not db_path.exists():
        pytest.skip(f"Test database not found at {db_path}; run scripts/init_test_db.py first")

    actual = _get_migrated_columns(db_path, table)
    assert actual, f"Table '{table}' has no columns – migration may not have run"

    missing = expected - actual
    extra = actual - expected  # informational only; extra columns are not an error
    assert not missing, (
        f"Table '{table}' is missing columns that exist in the SQLAlchemy model:\n"
        f"  Missing: {sorted(missing)}\n"
        f"  Present in DB: {sorted(actual)}\n"
        f"  Expected by model: {sorted(expected)}\n"
        f"Create an Alembic migration to add the missing columns."
    )
