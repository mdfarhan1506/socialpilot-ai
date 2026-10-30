"""Comments router.

POST /comments/             – add a comment (real or mock)
GET  /comments/?post_id=... – list comments for a post
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import deps, models
from ..models.comment import Comment

router = APIRouter()


class CommentCreate(BaseModel):
    workspace_id: str
    post_id: Optional[str] = None
    author: Optional[str] = None
    text: str


class CommentResponse(BaseModel):
    id: str
    workspace_id: str
    post_id: Optional[str]
    author: Optional[str]
    text: str
    created_at: str

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


@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    req: CommentCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(req.workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)

    comment = Comment(
        workspace_id=ws_uuid,
        post_id=req.post_id,
        author=req.author or current_user.email,
        text=req.text,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return CommentResponse(
        id=str(comment.id),
        workspace_id=str(comment.workspace_id),
        post_id=comment.post_id,
        author=comment.author,
        text=comment.text,
        created_at=comment.created_at.isoformat(),
    )


@router.get("/", response_model=List[CommentResponse])
async def list_comments(
    workspace_id: str = Query(...),
    post_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    ws_uuid = uuid.UUID(workspace_id)
    await _check_workspace_member(db, current_user, ws_uuid)

    q = select(Comment).where(Comment.workspace_id == ws_uuid)
    if post_id:
        q = q.where(Comment.post_id == post_id)
    result = await db.execute(q)
    comments = result.scalars().all()
    return [
        CommentResponse(
            id=str(c.id),
            workspace_id=str(c.workspace_id),
            post_id=c.post_id,
            author=c.author,
            text=c.text,
            created_at=c.created_at.isoformat(),
        )
        for c in comments
    ]
