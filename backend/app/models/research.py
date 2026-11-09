"""Research related models for trends and discovery."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class ResearchRun(Base):
    __tablename__ = "research_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    status = Column(String, default="pending")  # pending, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    parameters = Column(JSON, nullable=True)  # e.g., niche, sources
    result_summary = Column(Text, nullable=True)


class TrendOpportunity(Base):
    __tablename__ = "trend_opportunities"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    research_run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    evidence_url = Column(String, nullable=True)
    relevance_score = Column(String, nullable=True)
    source_name = Column(String, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    is_evergreen = Column(Boolean, default=False, nullable=False)
    trend_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
