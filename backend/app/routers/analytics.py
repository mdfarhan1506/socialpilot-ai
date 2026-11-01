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
from ..models.meta_token import MetaToken
from ..services.meta_insights import meta_insights
from ..utils.security import decrypt_token
from ..settings import settings

from ..models.autonomous import PostAnalyticsObservation

router = APIRouter()


async def _check_workspace_member(
    db: AsyncSession, user: models.User, workspace_id: uuid.UUID,
) -> models.Workspace:
    ws_result = await db.execute(
        select(models.Workspace).where(models.Workspace.id == workspace_id)
    )
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if ws.owner_id == user.id:
        return ws
    mem_result = await db.execute(
        select(models.WorkspaceMembership).where(
            models.WorkspaceMembership.workspace_id == workspace_id,
            models.WorkspaceMembership.user_id == user.id,
        )
    )
    if not mem_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this workspace")
    return ws


@router.get("/")
async def workspace_analytics(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return aggregated metrics for the workspace with verified provenance."""
    ws_uuid = uuid.UUID(workspace_id)
    ws = await _check_workspace_member(db, current_user, ws_uuid)

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

    # 4. Check for connected live Meta/Instagram account for the user or workspace owner
    meta_token_res = await db.execute(
        select(MetaToken).where(
            (MetaToken.user_id == current_user.id) | (MetaToken.user_id == ws.owner_id)
        ).order_by(MetaToken.updated_at.desc())
    )
    token_row = meta_token_res.scalars().first()

    instagram_live_data = None
    if token_row and token_row.encrypted_token and not settings.USE_MOCK:
        try:
            raw_token = decrypt_token(token_row.encrypted_token)
            instagram_live_data = await meta_insights.fetch_account_insights(
                ig_user_id=token_row.ig_user_id or "",
                access_token=raw_token,
            )
            # If dynamic resolution discovered the real ig_user_id, persist it to DB
            if (
                instagram_live_data
                and instagram_live_data.get("ig_user_id")
                and instagram_live_data.get("ig_user_id") != token_row.ig_user_id
            ):
                token_row.ig_user_id = instagram_live_data.get("ig_user_id")
                await db.commit()
        except Exception as exc:
            instagram_live_data = {
                "success": False,
                "error": f"Failed to decrypt or query Meta API: {str(exc)}",
            }

    # Decide reach display and live insight status
    has_live_insights = (
        instagram_live_data is not None
        and instagram_live_data.get("success")
        and instagram_live_data.get("insights_accessible")
    )
    has_live_profile = (
        instagram_live_data is not None
        and instagram_live_data.get("success")
        and instagram_live_data.get("profile_accessible")
    )

    if has_live_insights:
        live_reach = instagram_live_data.get("reach", 0)
        reach_display = str(live_reach)
        note = "Live account metrics and reach verified from Instagram Graph API."
    elif has_live_profile:
        reach_display = "0 (No 24h traffic)"
        note = (
            f"Instagram account (@{instagram_live_data.get('username', 'user')}) connected. "
            f"Followers: {instagram_live_data.get('followers_count', 0)}. "
            f"{instagram_live_data.get('error_note') or 'Account-level reach requires active audience engagement or 100+ followers.'}"
        )
    elif token_row and not settings.USE_MOCK:
        reach_display = "Account Connected"
        note = (
            instagram_live_data.get("error_note")
            or "Instagram account connected. Insights will update as posts receive engagement."
        )
    elif settings.USE_MOCK:
        reach_display = f"[MOCK] {total_reach}"
        note = "[MOCK] Simulated analytics active. Live metrics will be fetched from Meta Graph API when credentials are provided."
    else:
        reach_display = "Not Connected"
        note = "Connect an Instagram Professional account to view live performance insights."

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
        "estimated_reach": reach_display,
        "note": note,
        "instagram_connected": bool(token_row),
        "instagram_live_data": instagram_live_data,
    }
