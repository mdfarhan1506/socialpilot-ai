"""Analytics router – basic performance metrics.

GET /analytics/?workspace_id=... – aggregated metrics for a workspace.
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import deps, models
from ..models.comment import Comment
from ..models.content import ScheduledPost
from ..settings import settings

from ..models.autonomous import PostAnalyticsObservation

router = APIRouter()


async def _check_workspace_member(
    db: AsyncSession, user: models.User, workspace_id: uuid.UUID,
) -> None:
    ws_result = await db.execute(
        select(models.Workspace).where(models.Workspace.id == workspace_id)
    )
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if ws.owner_id == user.id:
        return
    mem_result = await db.execute(
        select(models.WorkspaceMembership).where(
            models.WorkspaceMembership.workspace_id == workspace_id,
            models.WorkspaceMembership.user_id == user.id,
        )
    )
    if not mem_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this workspace")


@router.get("/")
async def workspace_analytics(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return aggregated metrics for the workspace with verified provenance."""
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)

    sched_result = await db.execute(
        select(func.count()).select_from(ScheduledPost).where(
            ScheduledPost.workspace_id == ws_uuid,
            ScheduledPost.status == "scheduled",
        )
    )
    scheduled_count = sched_result.scalar() or 0

    comment_result = await db.execute(
        select(func.count()).select_from(Comment).where(Comment.workspace_id == ws_uuid)
    )
    comment_count = comment_result.scalar() or 0

    target_provenance = "mock_simulation" if settings.USE_MOCK else "live_meta_api"
    obs_res = await db.execute(
        select(
            func.sum(PostAnalyticsObservation.reach),
            func.sum(PostAnalyticsObservation.impressions),
            func.avg(PostAnalyticsObservation.engagement_rate),
            func.count(PostAnalyticsObservation.id),
        ).where(
            PostAnalyticsObservation.workspace_id == ws_uuid,
            PostAnalyticsObservation.data_provenance == target_provenance,
        )
    )
    row = obs_res.first()
    total_reach = row[0] if row and row[0] is not None else 0
    total_impressions = row[1] if row and row[1] is not None else 0
    avg_eng = row[2] if row and row[2] is not None else 0.0
    obs_count = row[3] if row and row[3] is not None else 0

    return {
        "workspace_id": workspace_id,
        "mock_mode": settings.USE_MOCK,
        "data_provenance": target_provenance,
        "scheduled_posts": scheduled_count,
        "total_comments": comment_count,
        "total_reach": total_reach,
        "total_impressions": total_impressions,
        "average_engagement_rate": round(float(avg_eng), 2),
        "observations_count": obs_count,
        "estimated_reach": f"[MOCK] {total_reach}" if settings.USE_MOCK else str(total_reach),
        "note": (
            "[MOCK] Simulated analytics active. Live metrics will be fetched from Meta Graph API when credentials are provided."
            if settings.USE_MOCK
            else "Live metrics ingested via Meta Graph API v19.0+ with verified provenance."
        ),
    }
