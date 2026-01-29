"""OAuth Token model for storing encrypted OAuth tokens."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class OAuthToken(Base):
    """OAuth Token model for storing encrypted access and refresh tokens.

    Tokens are encrypted using Fernet (AES-128-CBC) via the credential store
    before being persisted. This ensures tokens are protected at rest.
    """

    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_type = Column(String(50), nullable=False)  # 'snowflake', etc.

    # Encrypted token fields (encrypted via credential_store)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)

    # Token metadata
    token_type = Column(String(50), default="Bearer")
    scope = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to User
    user = relationship("User", backref="oauth_tokens")

    # Composite index for efficient lookups
    __table_args__ = (
        Index("ix_oauth_tokens_user_service", "user_id", "service_type", unique=True),
    )

    def __repr__(self) -> str:
        return f"<OAuthToken user_id={self.user_id} service={self.service_type}>"

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if token should be refreshed (expires within 5 minutes)."""
        if self.expires_at is None:
            return False
        from datetime import timedelta
        return datetime.utcnow() > (self.expires_at - timedelta(minutes=5))
