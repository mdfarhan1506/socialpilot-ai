"""Adaptive Scheduling Service — Phase 7.

Recommends posting time slots using real audience engagement data when
sufficient live observations exist.  When data is insufficient, returns
configurable hypothesis slots clearly labelled as such.

STRICT RULES:
- Never invent audience activity data or performance metrics.
- Hypothesis slots are always labelled with data_basis='hypothesis'.
- Evidence-based slots carry data_basis='live_data_verified' and the sample count.
- A minimum of MIN_LIVE_SAMPLES (5) PostAnalyticsObservation rows with
  data_provenance='live_meta_api' are required before switching from hypothesis
  to evidence-based recommendations.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.autonomous import PostAnalyticsObservation, StrategyInsight, AutomationAuditLog
from ..models.content import ScheduledPost

log = logging.getLogger(__name__)

# Minimum live observations needed before we trust performance-derived time slots.
MIN_LIVE_SAMPLES = 5

# Default hypothesis slots (UTC hour) used when real data is insufficient.
# Chosen as well-known cross-industry starting points; labelled clearly as hypotheses.
DEFAULT_HYPOTHESIS_SLOTS: List[int] = [9, 12, 17, 20]

# Default slot metadata explaining why they were chosen.
HYPOTHESIS_RATIONALE = (
    "These are configurable hypothesis slots based on common social media engagement patterns "
    "(9 AM, 12 PM, 5 PM, 8 PM UTC). They are NOT proven for this audience. "
    "Actual optimal times will be determined once sufficient real Instagram Insights data is collected."
)


async def recommend_posting_times(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    n_slots: int = 3,
) -> Dict[str, Any]:
    """Recommend posting time slots for a workspace.

    Returns:
        dict with keys:
          - recommended_hours: list[int] — UTC hours to post
          - data_basis: 'live_data_verified' | 'hypothesis'
          - samples_used: int
          - rationale: str — explains why these times were chosen
          - slots: list[dict] — detailed per-slot info with confidence
    """
    # 1. Count live observations for this workspace
    count_res = await db.execute(
        select(func.count(PostAnalyticsObservation.id)).where(
            PostAnalyticsObservation.workspace_id == workspace_id,
            PostAnalyticsObservation.data_provenance == "live_meta_api",
        )
    )
    live_count = count_res.scalar() or 0

    if live_count < MIN_LIVE_SAMPLES:
        log.info(
            "Workspace %s has %d live observations (need %d). Using hypothesis slots.",
            workspace_id, live_count, MIN_LIVE_SAMPLES,
        )
        slots = [
            {
                "hour_utc": h,
                "label": f"{h:02d}:00 UTC",
                "confidence": "low",
                "data_basis": "hypothesis",
                "note": HYPOTHESIS_RATIONALE,
            }
            for h in DEFAULT_HYPOTHESIS_SLOTS[:n_slots]
        ]
        return {
            "recommended_hours": DEFAULT_HYPOTHESIS_SLOTS[:n_slots],
            "data_basis": "hypothesis",
            "samples_used": live_count,
            "rationale": HYPOTHESIS_RATIONALE,
            "slots": slots,
        }

    # 2. Enough live data — derive posting hours from real engagement
    # Pull observations with their associated post's scheduled hour
    obs_res = await db.execute(
        select(PostAnalyticsObservation, ScheduledPost)
        .join(ScheduledPost, PostAnalyticsObservation.scheduled_post_id == ScheduledPost.id)
        .where(
            PostAnalyticsObservation.workspace_id == workspace_id,
            PostAnalyticsObservation.data_provenance == "live_meta_api",
        )
        .order_by(PostAnalyticsObservation.recorded_at.desc())
        .limit(100)
    )
    rows = obs_res.all()

    # Group engagement rates by UTC hour of publication
    hour_buckets: Dict[int, List[float]] = {}
    for obs, post in rows:
        if post.scheduled_time is None:
            continue
        hour = post.scheduled_time.hour
        if hour not in hour_buckets:
            hour_buckets[hour] = []
        hour_buckets[hour].append(obs.engagement_rate)

    if not hour_buckets:
        # Observations exist but can't determine hours — fall back to hypothesis
        log.warning("Workspace %s: live observations lack scheduled_time data. Using hypothesis.", workspace_id)
        return {
            "recommended_hours": DEFAULT_HYPOTHESIS_SLOTS[:n_slots],
            "data_basis": "hypothesis",
            "samples_used": live_count,
            "rationale": "Live observations found but scheduled_time unavailable. Using hypothesis slots.",
            "slots": [
                {"hour_utc": h, "label": f"{h:02d}:00 UTC", "confidence": "low",
                 "data_basis": "hypothesis", "note": HYPOTHESIS_RATIONALE}
                for h in DEFAULT_HYPOTHESIS_SLOTS[:n_slots]
            ],
        }

    # Sort hours by average engagement rate descending
    hour_avgs = {
        h: sum(rates) / len(rates)
        for h, rates in hour_buckets.items()
    }
    sorted_hours = sorted(hour_avgs.items(), key=lambda x: x[1], reverse=True)
    best_hours = [h for h, _ in sorted_hours[:n_slots]]

    # Pad to n_slots with hypothesis slots if fewer than n_slots real hours exist
    for h in DEFAULT_HYPOTHESIS_SLOTS:
        if len(best_hours) >= n_slots:
            break
        if h not in best_hours:
            best_hours.append(h)

    slots = []
    for h in best_hours[:n_slots]:
        avg_eng = hour_avgs.get(h)
        sample_count = len(hour_buckets.get(h, []))
        confidence = "high" if sample_count >= 10 else ("medium" if sample_count >= 3 else "low")
        note = (
            f"Derived from {sample_count} real Instagram Insights observations at this hour "
            f"(avg engagement rate: {avg_eng:.2f}%)."
            if avg_eng is not None
            else "Hour added from hypothesis defaults to reach requested slot count."
        )
        slots.append({
            "hour_utc": h,
            "label": f"{h:02d}:00 UTC",
            "confidence": confidence,
            "data_basis": "live_data_verified" if avg_eng is not None else "hypothesis",
            "avg_engagement_rate": round(avg_eng, 2) if avg_eng is not None else None,
            "samples": sample_count,
            "note": note,
        })

    rationale = (
        f"Posting times derived from {live_count} real Instagram Insights observations "
        f"across {len(hour_buckets)} publication hours. Hours ranked by average engagement rate."
    )

    return {
        "recommended_hours": [s["hour_utc"] for s in slots],
        "data_basis": "live_data_verified",
        "samples_used": live_count,
        "rationale": rationale,
        "slots": slots,
    }


async def get_best_hour_for_day(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    post_index: int = 0,
) -> Dict[str, Any]:
    """Get the single best posting hour for a given post-index-within-day.

    Args:
        post_index: 0-based index of the post within the day (used to pick different
                    hours for multi-post days).

    Returns:
        dict with 'hour_utc' (int) and 'data_basis' ('live_data_verified'|'hypothesis').
    """
    rec = await recommend_posting_times(db, workspace_id, n_slots=4)
    hours = rec["recommended_hours"]
    hour = hours[post_index % len(hours)] if hours else 14
    return {"hour_utc": hour, "data_basis": rec["data_basis"], "rationale": rec["rationale"]}
