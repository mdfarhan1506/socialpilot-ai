from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .. import schemas, models, deps

router = APIRouter()

@router.post("/", response_model=schemas.workspace.WorkspaceResponse)
async def create_workspace(ws: schemas.workspace.WorkspaceCreate, current_user: models.user.User = Depends(deps.get_current_user), db: AsyncSession = Depends(deps.get_db)):
    new_ws = models.workspace.Workspace(name=ws.name, owner_id=current_user.id)
    db.add(new_ws)
    await db.commit()
    await db.refresh(new_ws)
    # Add owner as membership
    membership = models.workspace.WorkspaceMembership(workspace_id=new_ws.id, user_id=current_user.id, is_admin=True)
    db.add(membership)
    await db.commit()
    await db.refresh(new_ws)
    return schemas.workspace.WorkspaceResponse.model_validate(new_ws)

@router.get("/", response_model=list[schemas.workspace.WorkspaceResponse])
async def list_workspaces(current_user: models.user.User = Depends(deps.get_current_user), db: AsyncSession = Depends(deps.get_db)):
    result = await db.execute(select(models.workspace.Workspace).where(models.workspace.Workspace.owner_id == current_user.id))
    workspaces = result.scalars().all()
    return [schemas.workspace.WorkspaceResponse.model_validate(ws) for ws in workspaces]

@router.post("/{workspace_id}/members", response_model=dict)
async def add_member(workspace_id: str, membership: schemas.workspace.MembershipCreate, current_user: models.user.User = Depends(deps.get_current_user), db: AsyncSession = Depends(deps.get_db)):
    # Verify current user is admin of workspace
    result = await db.execute(select(models.workspace.WorkspaceMembership).where(models.workspace.WorkspaceMembership.workspace_id == workspace_id, models.workspace.WorkspaceMembership.user_id == current_user.id, models.workspace.WorkspaceMembership.is_admin == True))
    admin_mem = result.scalar_one_or_none()
    if not admin_mem:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add members")
    # Create membership
    new_mem = models.workspace.WorkspaceMembership(workspace_id=workspace_id, user_id=membership.user_id, is_admin=membership.is_admin)
    db.add(new_mem)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to add member")
    return {"detail": "Member added"}
