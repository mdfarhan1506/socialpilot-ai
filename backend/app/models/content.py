"""Content related models"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class ContentIdea(Base):
    __tablename__ = "content_ideas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    generated_by = Column(String, nullable=True)  # e.g., "idea_engine"
    score = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContentPlan(Base):
    __tablename__ = "content_plans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idea_id = Column(UUID(as_uuid=True), ForeignKey("content_ideas.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    plan_data = Column(JSON, nullable=False)  # structured plan details
    status = Column(String, default="draft")  # draft, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContentAsset(Base):
    __tablename__ = "content_assets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("content_plans.id"), nullable=False)
    asset_type = Column(String, nullable=False)  # image, video, carousel, etc.
    url = Column(String, nullable=False)  # location in object storage
    asset_metadata = Column(JSON, nullable=True)  # additional metadata for asset
    created_at = Column(DateTime, default=datetime.utcnow)

class ContentDraft(Base):
    __tablename__ = "content_drafts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("content_plans.id"), nullable=False)
    caption = Column(Text, nullable=True)
    assets = Column(JSON, nullable=True)  # list of asset ids
    quality_score = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Optional FK to a draft (may be None when scheduling directly via API)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("content_drafts.id"), nullable=True)
    # Direct fields used by the scheduling router
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    caption = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String, default="scheduled")  # scheduled, published, failed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PublishedPost(Base):
    __tablename__ = "published_posts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheduled_post_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_posts.id"), nullable=False)
    platform_post_id = Column(String, nullable=True)  # Instagram media ID
    published_at = Column(DateTime, nullable=True)
    status = Column(String, default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
