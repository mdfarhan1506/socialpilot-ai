"""Autonomous Creator Router.

Controls policies, schedules, rolling plans, strategy insights, and audit logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .. import deps, models
from ..models.autonomous import AutonomousConfig, StrategyInsight, AutomationAuditLog
from ..models.content import ScheduledPost
from ..services.autonomous_engine import autonomous_engine

router = APIRouter()


class ConfigUpdate(BaseModel):
    workspace_id: str
    is_active: Optional[bool] = None
    approval_mode: Optional[str] = None
    min_posts_per_day: Optional[int] = None
    max_posts_per_day: Optional[int] = None
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    restricted_keywords: Optional[List[str]] = None
    target_topics: Optional[List[str]] = None


async def _check_workspace_member(
    db: AsyncSession, user: models.User, workspace_id: uuid.UUID
) -> models.Workspace:
    ws_res = await db.execute(select(models.Workspace).where(models.Workspace.id == workspace_id))
    ws = ws_res.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if ws.owner_id == user.id:
        return ws
    mem_res = await db.execute(
        select(models.WorkspaceMembership).where(
            models.WorkspaceMembership.workspace_id == workspace_id,
            models.WorkspaceMembership.user_id == user.id,
        )
    )
    if not mem_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this workspace")
    return ws


@router.get("/config")
async def get_config(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    cfg = await autonomous_engine.get_or_create_config(db, ws_uuid)
    return {
        "id": str(cfg.id),
        "workspace_id": str(cfg.workspace_id),
        "is_active": cfg.is_active,
        "approval_mode": cfg.approval_mode,
        "min_posts_per_day": cfg.min_posts_per_day,
        "max_posts_per_day": cfg.max_posts_per_day,
        "quiet_hours_start": cfg.quiet_hours_start,
        "quiet_hours_end": cfg.quiet_hours_end,
        "restricted_keywords": cfg.restricted_keywords or [],
        "target_topics": cfg.target_topics or [],
    }


@router.put("/config")
async def update_config(
    req: ConfigUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(req.workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    cfg = await autonomous_engine.get_or_create_config(db, ws_uuid)

    if req.is_active is not None:
        cfg.is_active = req.is_active
    if req.approval_mode is not None:
        cfg.approval_mode = req.approval_mode
    if req.min_posts_per_day is not None:
        cfg.min_posts_per_day = req.min_posts_per_day
    if req.max_posts_per_day is not None:
        cfg.max_posts_per_day = req.max_posts_per_day
    if req.quiet_hours_start is not None:
        cfg.quiet_hours_start = req.quiet_hours_start
    if req.quiet_hours_end is not None:
        cfg.quiet_hours_end = req.quiet_hours_end
    if req.restricted_keywords is not None:
        cfg.restricted_keywords = req.restricted_keywords
    if req.target_topics is not None:
        cfg.target_topics = req.target_topics

    await db.commit()
    await db.refresh(cfg)
    return {"status": "updated", "is_active": cfg.is_active}


@router.post("/pause")
async def pause_autonomous(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    cfg = await autonomous_engine.get_or_create_config(db, ws_uuid)
    cfg.is_active = False

    audit = AutomationAuditLog(
        workspace_id=ws_uuid,
        action="policy_pause",
        status="success",
        summary=f"Autonomous creator paused by user {current_user.email}",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(audit)
    await db.commit()
    return {"status": "paused", "is_active": False}


@router.post("/resume")
async def resume_autonomous(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    cfg = await autonomous_engine.get_or_create_config(db, ws_uuid)
    cfg.is_active = True

    audit = AutomationAuditLog(
        workspace_id=ws_uuid,
        action="policy_resume",
        status="success",
        summary=f"Autonomous creator resumed by user {current_user.email}",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(audit)
    await db.commit()
    return {"status": "resumed", "is_active": True}


@router.post("/run-cycle")
async def run_cycle(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    result = await autonomous_engine.run_autonomous_cycle(db, ws_uuid)
    return result


@router.get("/insights")
async def get_insights(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    res = await db.execute(
        select(StrategyInsight)
        .where(StrategyInsight.workspace_id == ws_uuid)
        .order_by(desc(StrategyInsight.created_at))
        .limit(20)
    )
    insights = res.scalars().all()
    return [
        {
            "id": str(i.id),
            "topic": i.topic,
            "hook_type": i.hook_type,
            "format_type": i.format_type,
            "best_time_slot": i.best_time_slot,
            "performance_score": i.performance_score,
            "hypothesis": i.hypothesis,
            "recommendation": i.recommendation,
            "confidence_score": i.confidence_score,
            "is_mock": i.is_mock,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in insights
    ]


@router.get("/audit-logs")
async def get_audit_logs(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    res = await db.execute(
        select(AutomationAuditLog)
        .where(AutomationAuditLog.workspace_id == ws_uuid)
        .order_by(desc(AutomationAuditLog.created_at))
        .limit(50)
    )
    logs = res.scalars().all()
    return [
        {
            "id": str(l.id),
            "action": l.action,
            "status": l.status,
            "summary": l.summary,
            "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.get("/plan")
async def get_rolling_plan(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    res = await db.execute(
        select(ScheduledPost)
        .where(
            ScheduledPost.workspace_id == ws_uuid,
            ScheduledPost.scheduled_time >= now,
        )
        .order_by(ScheduledPost.scheduled_time.asc())
        .limit(30)
    )
    posts = res.scalars().all()
    return [
        {
            "id": str(p.id),
            "concept": p.concept,
            "hook": p.hook,
            "script_or_body": p.script_or_body,
            "call_to_action": p.call_to_action,
            "caption": p.caption,
            "image_url": p.image_url,
            "scheduled_time": p.scheduled_time.isoformat() if p.scheduled_time else None,
            "status": p.status,
            "requires_approval": bool(p.requires_approval),
            "approved_at": p.approved_at.isoformat() if p.approved_at else None,
        }
        for p in posts
    ]


@router.post("/posts/{post_id}/approve")
async def approve_post(
    post_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    pid = uuid.UUID(post_id)
    res = await db.execute(select(ScheduledPost).where(ScheduledPost.id == pid))
    post = res.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    await _check_workspace_member(db, current_user, post.workspace_id)

    post.requires_approval = False
    post.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    post.status = "scheduled"

    audit = AutomationAuditLog(
        workspace_id=post.workspace_id,
        action="approval",
        status="success",
        summary=f"Post approved by {current_user.email} for publication at {post.scheduled_time}",
        details={"post_id": str(post.id)},
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(audit)
    await db.commit()
    return {"status": "approved", "post_id": str(post.id)}
