"""TODO Item Pydantic schemas for manual work tracking."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class TodoCategory(str, Enum):
    """Categories of TODO items."""

    STORED_PROCEDURE = "stored_procedure"
    EXPRESSION = "expression"
    SUBREPORT = "subreport"
    CUSTOM_CODE = "custom_code"
    UNSUPPORTED_VISUAL = "unsupported_visual"


class TodoPriority(str, Enum):
    """Priority levels for TODO items."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TodoItemBase(BaseModel):
    """Base TODO item schema."""

    title: str
    category: TodoCategory
    priority: TodoPriority
    location: str
    item_name: str | None = None
    guidance: str
    original_content: str | None = None


class TodoItemCreate(TodoItemBase):
    """Schema for creating a TODO item."""

    analysis_id: int | UUID  # Can be int (from DB) or UUID (during generation)


class TodoItem(TodoItemBase):
    """Complete TODO item schema with database fields."""

    id: int
    analysis_id: int | UUID  # Can be int (from DB) or UUID (from generator)
    is_resolved: bool = False
    resolved_at: datetime | None = None
    resolved_by: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TodoItemUpdate(BaseModel):
    """Schema for updating a TODO item."""

    is_resolved: bool | None = None


class TodoListSummary(BaseModel):
    """Summary counts for a TODO list."""

    total_count: int = 0
    high_priority_count: int = 0
    medium_priority_count: int = 0
    low_priority_count: int = 0
    resolved_count: int = 0
    unresolved_count: int = 0

    @computed_field
    @property
    def completion_percentage(self) -> float:
        """Percentage of resolved items."""
        if self.total_count == 0:
            return 100.0
        return round((self.resolved_count / self.total_count) * 100, 1)


class TodoListResponse(BaseModel):
    """Response schema for a TODO list."""

    items: list[TodoItem] = Field(default_factory=list)
    summary: TodoListSummary = Field(default_factory=TodoListSummary)

    # Grouped items for display
    high_priority_items: list[TodoItem] = Field(default_factory=list)
    medium_priority_items: list[TodoItem] = Field(default_factory=list)
    low_priority_items: list[TodoItem] = Field(default_factory=list)

    # Grouped by category
    by_category: dict[str, list[TodoItem]] = Field(default_factory=dict)

    @classmethod
    def from_items(cls, items: list[TodoItem]) -> "TodoListResponse":
        """Create response from list of items with computed groupings."""
        summary = TodoListSummary(
            total_count=len(items),
            high_priority_count=sum(1 for i in items if i.priority == TodoPriority.HIGH),
            medium_priority_count=sum(
                1 for i in items if i.priority == TodoPriority.MEDIUM
            ),
            low_priority_count=sum(1 for i in items if i.priority == TodoPriority.LOW),
            resolved_count=sum(1 for i in items if i.is_resolved),
            unresolved_count=sum(1 for i in items if not i.is_resolved),
        )

        # Group by priority
        high_priority = [i for i in items if i.priority == TodoPriority.HIGH]
        medium_priority = [i for i in items if i.priority == TodoPriority.MEDIUM]
        low_priority = [i for i in items if i.priority == TodoPriority.LOW]

        # Group by category
        by_category: dict[str, list[TodoItem]] = {}
        for item in items:
            cat_key = item.category.value
            if cat_key not in by_category:
                by_category[cat_key] = []
            by_category[cat_key].append(item)

        return cls(
            items=items,
            summary=summary,
            high_priority_items=high_priority,
            medium_priority_items=medium_priority,
            low_priority_items=low_priority,
            by_category=by_category,
        )


class EmptyTodoListResponse(BaseModel):
    """Response for reports with no TODO items."""

    message: str = "No manual work items identified"
    can_proceed_to_conversion: bool = True
    summary: TodoListSummary = Field(default_factory=TodoListSummary)
