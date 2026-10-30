"""Comment model for storing Instagram post comments (real or mock)."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class Comment(Base):
    __tablename__ = "comments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    post_id = Column(String, nullable=True)          # Instagram media ID or internal ID
    author = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    platform_comment_id = Column(String, nullable=True)  # Instagram comment ID
    created_at = Column(DateTime, default=datetime.utcnow)
