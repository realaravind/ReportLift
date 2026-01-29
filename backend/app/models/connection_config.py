"""Connection Configuration model for storing encrypted service credentials."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.models.base import Base


class ConnectionConfig(Base):
    """Model for storing encrypted connection configurations.

    Credentials are encrypted using Fernet before storage and decrypted
    when retrieved. The encrypted_config field stores a JSON blob of
    service-specific configuration values.
    """

    __tablename__ = "connection_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Service type: 'ssrs', 'snowflake', 'ollama'
    service_type = Column(String(50), unique=True, nullable=False, index=True)

    # Encrypted JSON configuration blob
    # Contains service-specific settings with sensitive values encrypted
    encrypted_config = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ConnectionConfig {self.service_type}>"
