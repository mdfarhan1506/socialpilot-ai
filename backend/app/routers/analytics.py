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
    """Return aggregated metrics for the workspace.

    Access is restricted to workspace owner/members.
    In mock mode all counts are real DB counts; reach data is clearly labeled mock.
    """
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

    return {
        "workspace_id": workspace_id,
        "mock_mode": settings.USE_MOCK,
        "scheduled_posts": scheduled_count,
        "total_comments": comment_count,
        "estimated_reach": "[MOCK] 0" if settings.USE_MOCK else "N/A – real analytics require Meta Insights API",
        "note": (
            "[MOCK] Analytics are DB counts only. Real reach/impression data requires "
            "Meta Graph API Insights with pages_read_engagement permission."
            if settings.USE_MOCK
            else "Real analytics from Meta Insights API not yet implemented."
        ),
    }
