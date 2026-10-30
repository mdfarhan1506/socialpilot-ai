from pydantic import BaseModel, UUID4, Field, ConfigDict
from datetime import datetime

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID4
    name: str
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime

class MembershipCreate(BaseModel):
    user_id: UUID4
    is_admin: bool = False
