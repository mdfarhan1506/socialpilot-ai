from pydantic import BaseModel, UUID4
from datetime import datetime

class BrandProfileCreate(BaseModel):
    workspace_id: UUID4
    niche: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    brand_voice: str | None = None
    content_preferences: str | None = None

class BrandProfileUpdate(BaseModel):
    niche: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    brand_voice: str | None = None
    content_preferences: str | None = None

class BrandProfileResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    workspace_id: UUID4
    niche: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    brand_voice: str | None = None
    content_preferences: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
