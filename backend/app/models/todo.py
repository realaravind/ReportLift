"""TodoItem model for tracking manual work items."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.schemas.todo import TodoCategory, TodoPriority


class TodoItem(Base):
    """TodoItem model for tracking manual work items from analysis.

    Each TODO item represents a piece of work that requires manual
    attention during report conversion (SP conversion, expression
    rewriting, visual recreation, etc.)
    """

    __tablename__ = "todo_items"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Link to analysis
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    analysis = relationship("Analysis", backref="todo_item_records")

    # TODO item details
    title = Column(String(500), nullable=False)
    category = Column(
        Enum(TodoCategory, native_enum=False, length=50),
        nullable=False,
    )
    priority = Column(
        Enum(TodoPriority, native_enum=False, length=20),
        nullable=False,
    )
    location = Column(String(500), nullable=True)
    item_name = Column(String(255), nullable=True)
    guidance = Column(Text, nullable=True)
    original_content = Column(Text, nullable=True)

    # Resolution tracking
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by = relationship("User", backref="resolved_todos")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        status = "resolved" if self.is_resolved else "pending"
        return f"<TodoItem {self.id} [{self.category.value}] {status}>"

    def mark_resolved(self, user_id: int | None = None) -> None:
        """Mark this TODO item as resolved."""
        self.is_resolved = True
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by_id = user_id

    def mark_unresolved(self) -> None:
        """Mark this TODO item as unresolved."""
        self.is_resolved = False
        self.resolved_at = None
        self.resolved_by_id = None
