"""User model for caching AD identity information."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.models.base import Base


class User(Base):
    """User model for storing AD identity cache.

    Note: This is a cache of AD user information, not a primary auth store.
    Authentication is performed against Active Directory.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False)
    full_identity = Column(String(511), nullable=False, unique=True)  # DOMAIN\username
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    # Timestamps
    first_login = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User {self.full_identity}>"
