"""Scheduling router.

POST /schedule/         – schedule a post
GET  /schedule/         – list scheduled posts (workspace-scoped)
DELETE /schedule/{id}   – cancel a scheduled post
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import deps, models
from ..models.content import ScheduledPost

router = APIRouter()


class ScheduleRequest(BaseModel):
    caption: str
    image_url: Optional[str] = None
    scheduled_time: datetime  # ISO-8601, must be in the future
    workspace_id: str


class ScheduleResponse(BaseModel):
    id: str
    caption: str
    image_url: Optional[str]
    scheduled_time: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


async def _check_workspace_member(
    db: AsyncSession, user: models.User, workspace_id: uuid.UUID,
) -> None:
    """Verify user is owner or member of the workspace, else raise 403."""
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


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ScheduleResponse)
async def create_schedule(
    req: ScheduleRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(req.workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)

    # Validate future time
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    sched = req.scheduled_time.replace(tzinfo=None) if req.scheduled_time.tzinfo else req.scheduled_time
    if sched <= now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scheduled_time must be in the future",
        )

    # Detect duplicate: same workspace + caption + scheduled_time
    dup = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.caption == req.caption,
            ScheduledPost.workspace_id == ws_uuid,
            ScheduledPost.scheduled_time == sched,
            ScheduledPost.status == "scheduled",
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate scheduled post detected (same caption, workspace, and time)",
        )

    post = ScheduledPost(
        caption=req.caption,
        image_url=req.image_url,
        workspace_id=ws_uuid,
        user_id=current_user.id,
        scheduled_time=sched,
        status="scheduled",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return ScheduleResponse(
        id=str(post.id),
        caption=post.caption,
        image_url=post.image_url,
        scheduled_time=post.scheduled_time,
        status=post.status,
        created_at=post.created_at,
    )


@router.get("/", response_model=List[ScheduleResponse])
async def list_schedules(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)

    result = await db.execute(
        select(ScheduledPost).where(ScheduledPost.workspace_id == ws_uuid)
    )
    posts = result.scalars().all()
    return [
        ScheduleResponse(
            id=str(p.id),
            caption=p.caption,
            image_url=p.image_url,
            scheduled_time=p.scheduled_time,
            status=p.status,
            created_at=p.created_at,
        )
        for p in posts
    ]


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    sid = uuid.UUID(schedule_id)
    result = await db.execute(select(ScheduledPost).where(ScheduledPost.id == sid))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled post not found")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    post.status = "cancelled"
    await db.commit()
    return None
