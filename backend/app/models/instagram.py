"""Instagram related models"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    instagram_user_id = Column(String, nullable=False, unique=True)  # Instagram numeric ID
    username = Column(String, nullable=False)
    is_connected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OAuthCredential(Base):
    __tablename__ = "oauth_credentials"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instagram_account_id = Column(UUID(as_uuid=True), ForeignKey("instagram_accounts.id"), nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
