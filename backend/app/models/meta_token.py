"""Encrypted Meta (Instagram) access token storage.

Tokens are stored encrypted using Fernet symmetric encryption.
The ENCRYPTION_KEY setting must be a 32-byte URL-safe base64-encoded key.
Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class MetaToken(Base):
    __tablename__ = "meta_tokens"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    ig_user_id = Column(String, nullable=True)          # Instagram Business Account ID
    encrypted_token = Column(Text, nullable=False)       # Fernet-encrypted access token
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
