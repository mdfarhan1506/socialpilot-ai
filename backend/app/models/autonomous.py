"""Autonomous Creator models for policy, learning, audit, and analytics observations."""
from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Boolean, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class AutonomousConfig(Base):
    """Workspace-level configuration and policy controls for the autonomous creator."""
    __tablename__ = "autonomous_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), unique=True, nullable=False)
    
    # Global state for workspace: True = Running, False = Paused
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Approval policy: "auto" (direct schedule) or "manual_for_sensitive"
    approval_mode = Column(String, default="manual_for_sensitive", nullable=False)
    
    # Adaptive scheduling parameters
    min_posts_per_day = Column(Integer, default=1, nullable=False)
    max_posts_per_day = Column(Integer, default=3, nullable=False)
    
    # Quiet hours (0-23 in UTC). e.g. 22 to 7
    quiet_hours_start = Column(Integer, default=22, nullable=False)
    quiet_hours_end = Column(Integer, default=7, nullable=False)
    
    # Content restrictions (list of prohibited strings/topics)
    restricted_keywords = Column(JSON, default=list, nullable=True)
    
    # Preferred topics / content pillars
    target_topics = Column(JSON, default=list, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyInsight(Base):
    """Learning engine hypotheses and strategy recommendations derived from historical performance."""
    __tablename__ = "strategy_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    topic = Column(String, nullable=False)
    hook_type = Column(String, nullable=True)     # e.g., "question", "statistic", "bold_statement", "story"
    format_type = Column(String, nullable=True)   # e.g., "carousel", "single_image", "short_text"
    best_time_slot = Column(String, nullable=True) # e.g., "14:00-16:00 UTC"
    
    performance_score = Column(Float, default=0.0)
    hypothesis = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.5)
    
    # Provenance flag: True if derived from simulated/mock metrics.
    # CRITICAL: Mock insights are NEVER used to adjust live production strategy.
    is_mock = Column(Boolean, default=True, nullable=False)
    
    evidence_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostAnalyticsObservation(Base):
    """Recurring time-series performance observations for published posts."""
    __tablename__ = "post_analytics_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    scheduled_post_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_posts.id"), nullable=False)
    platform_post_id = Column(String, nullable=True)
    
    post_age_hours = Column(Float, default=0.0, nullable=False)
    impressions = Column(Integer, default=0, nullable=False)
    reach = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    saves = Column(Integer, default=0, nullable=False)
    engagement_rate = Column(Float, default=0.0, nullable=False)
    
    # Provenance: "live_meta_api" or "mock_simulation"
    data_provenance = Column(String, default="mock_simulation", nullable=False)
    
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AutomationAuditLog(Base):
    """Immutable audit trail of all autonomous decisions and actions."""
    __tablename__ = "automation_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    # action: "research", "plan_generation", "content_synthesis", "media_validation", 
    #         "adaptive_schedule", "publish", "analytics_poll", "strategy_update", "policy_pause", "approval"
    action = Column(String, nullable=False)
    status = Column(String, default="success")  # "success", "blocked", "warning", "failed"
    summary = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
