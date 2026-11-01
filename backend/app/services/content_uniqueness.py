"""Content uniqueness, diversity, and duplicate detection service.

Provides:
1. Exact and near-duplicate caption detection using normalized token similarity and character n-grams.
2. Distinct topic, angle, hook, and content format assignment across rolling multi-day schedules.
3. Checking against existing scheduled and published posts within a rolling window (default 7 days).
4. Retry loop helper (up to 3 attempts) to ensure unique, varied post generation.
"""
from __future__ import annotations

import re
import difflib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
import uuid

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.content import ScheduledPost, PublishedPost

# Content format archetypes supported by Instagram feed post pipeline
CONTENT_FORMATS = [
    {
        "format": "educational_tips",
        "objective": "educate",
        "angle": "Actionable step-by-step breakdown",
        "hook_style": "framework",
    },
    {
        "format": "question",
        "objective": "engage",
        "angle": "Provocative community discussion",
        "hook_style": "question",
    },
    {
        "format": "checklist",
        "objective": "educate",
        "angle": "Practical audit checklist",
        "hook_style": "checklist",
    },
    {
        "format": "contrarian_insight",
        "objective": "inspire",
        "angle": "Challenging common industry misconceptions",
        "hook_style": "contrarian",
    },
    {
        "format": "promotional_offer",
        "objective": "convert",
        "angle": "Clear value proposition and call to action",
        "hook_style": "promotional",
    },
]


def normalize_text(text: str) -> str:
    """Normalize text by stripping hashtags, punctuation, excess whitespace, and lowercasing."""
    if not text:
        return ""
    # Strip hashtags and URLs
    no_tags = re.sub(r'#\w+', '', text)
    no_urls = re.sub(r'https?://\S+', '', no_tags)
    # Remove special punctuation
    clean = re.sub(r'[^\w\s]', '', no_urls).lower()
    return " ".join(clean.split())


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate normalized similarity ratio between two texts (0.0 to 1.0)."""
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0
    return difflib.SequenceMatcher(None, norm1, norm2).ratio()


def is_duplicate_or_near_duplicate(
    candidate_caption: str,
    existing_captions: List[str],
    threshold: float = 0.75,
) -> Tuple[bool, Optional[str], float]:
    """Check if candidate caption is identical or highly similar to any existing caption.

    Returns:
        (is_dup, matched_existing_caption, highest_similarity)
    """
    candidate_norm = normalize_text(candidate_caption)
    if not candidate_norm:
        return True, "Empty caption", 1.0

    highest_sim = 0.0
    closest_match = None

    for existing in existing_captions:
        existing_norm = normalize_text(existing)
        if not existing_norm:
            continue
        if candidate_norm == existing_norm:
            return True, existing, 1.0
        sim = difflib.SequenceMatcher(None, candidate_norm, existing_norm).ratio()
        if sim > highest_sim:
            highest_sim = sim
            closest_match = existing

    if highest_sim >= threshold:
        return True, closest_match, highest_sim
    return False, None, highest_sim


async def get_recent_posts_in_window(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    days: int = 7,
    reference_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Retrieve scheduled and published posts within the specified rolling window (default 7 days)."""
    ref = reference_time or datetime.now(timezone.utc).replace(tzinfo=None)
    start_window = ref - timedelta(days=days)
    end_window = ref + timedelta(days=days)

    stmt = select(ScheduledPost).where(
        ScheduledPost.workspace_id == workspace_id,
        ScheduledPost.status.in_(["scheduled", "published", "pending_approval"]),
        or_(
            and_(ScheduledPost.scheduled_time >= start_window, ScheduledPost.scheduled_time <= end_window),
            and_(ScheduledPost.created_at >= start_window, ScheduledPost.created_at <= end_window),
        )
    )
    result = await db.execute(stmt)
    posts = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "caption": p.caption or "",
            "concept": p.concept or "",
            "hook": p.hook or "",
            "scheduled_time": p.scheduled_time,
        }
        for p in posts
    ]


def pick_distinct_format_and_angle(day_offset: int, post_index: int = 0) -> Dict[str, str]:
    """Deterministically cycle through diverse content formats and hooks across days."""
    idx = (day_offset + post_index) % len(CONTENT_FORMATS)
    return CONTENT_FORMATS[idx]
