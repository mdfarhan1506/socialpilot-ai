from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from typing import List

from .. import models, schemas, deps
from ..models.brand import BrandProfile

router = APIRouter()

async def _get_workspace(db: AsyncSession, user: models.User, workspace_id: str):
    """Return the workspace if the user is owner or member, otherwise raise 403/404."""
    ws_id = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id
    result = await db.execute(select(models.Workspace).where(models.Workspace.id == ws_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    # membership check
    result = await db.execute(
        select(models.WorkspaceMembership)
        .where(models.WorkspaceMembership.workspace_id == ws_id)
        .where(models.WorkspaceMembership.user_id == user.id)
    )
    membership = result.scalar_one_or_none()
    if workspace.owner_id != user.id and not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this workspace")
    return workspace

@router.post("/", response_model=schemas.brand.BrandProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_in: schemas.brand.BrandProfileCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    await _get_workspace(db, current_user, str(brand_in.workspace_id))
    brand = BrandProfile(
        user_id=current_user.id,
        workspace_id=brand_in.workspace_id,
        niche=brand_in.niche,
        target_audience=brand_in.target_audience,
        tone=brand_in.tone,
        brand_voice=brand_in.brand_voice,
        content_preferences=brand_in.content_preferences,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand

@router.get("/", response_model=List[schemas.brand.BrandProfileResponse])
async def list_brands(
    workspace_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    await _get_workspace(db, current_user, workspace_id)
    ws_id = uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id
    result = await db.execute(select(BrandProfile).where(BrandProfile.workspace_id == ws_id))
    return result.scalars().all()

@router.get("/{brand_id}", response_model=schemas.brand.BrandProfileResponse)
async def get_brand(
    brand_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    brand_uuid = uuid.UUID(brand_id) if isinstance(brand_id, str) else brand_id
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == brand_uuid))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    await _get_workspace(db, current_user, str(brand.workspace_id))
    return brand

@router.put("/{brand_id}", response_model=schemas.brand.BrandProfileResponse)
async def update_brand(
    brand_id: str,
    brand_in: schemas.brand.BrandProfileUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    brand_uuid = uuid.UUID(brand_id) if isinstance(brand_id, str) else brand_id
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == brand_uuid))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    await _get_workspace(db, current_user, str(brand.workspace_id))
    for attr, value in brand_in.dict(exclude_unset=True).items():
        setattr(brand, attr, value)
    await db.commit()
    await db.refresh(brand)
    return brand

@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    brand_uuid = uuid.UUID(brand_id) if isinstance(brand_id, str) else brand_id
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == brand_uuid))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    await _get_workspace(db, current_user, str(brand.workspace_id))
    await db.delete(brand)
    await db.commit()
    return None
