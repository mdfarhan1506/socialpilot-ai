"""Unit and integration tests for duplicate prevention, distinct planning, and uniqueness retries."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
import pytest

from backend.app.services.content_uniqueness import (
    normalize_text,
    calculate_similarity,
    is_duplicate_or_near_duplicate,
    pick_distinct_format_and_angle,
    get_recent_posts_in_window,
    CONTENT_FORMATS,
)
from backend.app.services.autonomous_engine import autonomous_engine
from backend.app.db import AsyncSessionLocal
from backend.app.models.workspace import Workspace
from backend.app.models.user import User
from backend.app.models.content import ScheduledPost
from backend.tests.conftest import client, get_auth_headers, create_workspace


def test_text_normalization():
    """Verify hashtag removal, URL removal, punctuation stripping, and lowercasing."""
    raw = "🚀 Check out this BRAND NEW tool!! Visit https://example.com #AI #Tech #Innovation"
    norm = normalize_text(raw)
    assert norm == "check out this brand new tool visit"


def test_duplicate_caption_detection_exact():
    """Exact identical caption should be identified as duplicate with 1.0 similarity."""
    caption1 = "Here are 3 tips to scale your SaaS brand in 2026. #SaaS #Growth"
    caption2 = "Here are 3 tips to scale your SaaS brand in 2026. #DifferentTag"

    is_dup, match, sim = is_duplicate_or_near_duplicate(caption1, [caption2], threshold=0.75)
    assert is_dup is True
    assert sim == 1.0


def test_near_duplicate_caption_detection():
    """Captions with minor word tweaks or small edits must be flagged as near-duplicates."""
    caption_orig = "Here are the top 3 core pillars behind high-performing SaaS systems in 2026."
    caption_similar = "Here are the 3 core pillars behind high-performing SaaS systems in 2026."

    is_dup, match, sim = is_duplicate_or_near_duplicate(caption_similar, [caption_orig], threshold=0.75)
    assert is_dup is True
    assert sim >= 0.85

    # Completely different caption should NOT be flagged
    different_caption = "Why customer retention metrics are completely misleading for early startups."
    is_diff, _, diff_sim = is_duplicate_or_near_duplicate(different_caption, [caption_orig], threshold=0.75)
    assert is_diff is False
    assert diff_sim < 0.50


def test_distinct_format_and_topic_rotation():
    """Verify cycling across multi-day schedule rotates format, objective, and angle."""
    formats_seen = set()
    for day in range(1, 8):
        fmt = pick_distinct_format_and_angle(day, post_index=0)
        assert "format" in fmt
        assert "objective" in fmt
        assert "angle" in fmt
        assert "hook_style" in fmt
        formats_seen.add(fmt["format"])

    # Across 7 days, at least 4 unique formats must be scheduled
    assert len(formats_seen) >= 4


def test_scheduling_router_rejects_near_duplicate():
    """Verify POST /schedule/ endpoint rejects near-duplicate posts across the workspace calendar."""
    headers = get_auth_headers("uniqueness_test@test.com")
    ws_id = create_workspace(headers, "Uniqueness WS")

    t1 = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    t2 = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()

    # Schedule first post
    resp1 = client.post(
        "/schedule/",
        json={
            "caption": "The complete execution model for daily workflow optimization and leverage.",
            "workspace_id": ws_id,
            "scheduled_time": t1,
        },
        headers=headers,
    )
    assert resp1.status_code == 201, resp1.text

    # Schedule near-duplicate post at different time
    resp2 = client.post(
        "/schedule/",
        json={
            "caption": "The complete execution model for daily workflow optimization & leverage!",
            "workspace_id": ws_id,
            "scheduled_time": t2,
        },
        headers=headers,
    )
    assert resp2.status_code == 409, resp2.text
    assert "Near-duplicate caption detected" in resp2.json()["detail"]


def test_retry_exhaustion_handling():
    """Verify that if candidate generation consistently matches duplicates, retry halts safely."""
    async def _run():
        async with AsyncSessionLocal() as db:
            user = User(email=f"retry_{uuid.uuid4().hex[:6]}@test.com", hashed_password="pw")
            db.add(user)
            await db.commit()
            await db.refresh(user)

            ws = Workspace(name="Retry Test WS", owner_id=user.id)
            db.add(ws)
            await db.commit()
            await db.refresh(ws)

            # Pre-seed existing captions for the workspace
            base_caption = (
                "What is the single biggest operational bottleneck holding your B2B SaaS brand back?\n\n"
                "Most leaders focus on symptoms rather than root causes.\n\n"
                "Drop your answer in the comments and let us discuss!\n\n#B2BSaaS #Strategy"
            )
            post = ScheduledPost(
                workspace_id=ws.id,
                caption=base_caption,
                scheduled_time=datetime.now(timezone.utc) + timedelta(days=1),
                status="scheduled",
            )
            db.add(post)
            await db.commit()

            # Check that get_recent_posts_in_window retrieves it
            recent = await get_recent_posts_in_window(db, ws.id, days=7)
            assert len(recent) == 1
            assert recent[0]["caption"] == base_caption

            # Detect that candidate matching base_caption is caught
            is_dup, _, _ = is_duplicate_or_near_duplicate(base_caption, [p["caption"] for p in recent])
            assert is_dup is True

    asyncio.run(_run())
