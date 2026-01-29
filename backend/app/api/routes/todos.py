"""TODO Items API routes."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.analysis import Analysis
from app.models.todo import TodoItem as TodoItemModel
from app.models.user import User
from app.schemas.todo import (
    EmptyTodoListResponse,
    TodoCategory,
    TodoItem,
    TodoItemUpdate,
    TodoListResponse,
    TodoListSummary,
    TodoPriority,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/todos", tags=["todos"])


@router.get(
    "/analysis/{analysis_id}",
    response_model=TodoListResponse | EmptyTodoListResponse,
    summary="Get TODO list for an analysis",
    description="Retrieve all TODO items for a specific analysis, sorted by priority and grouped by category.",
)
async def get_todos_for_analysis(
    analysis_id: int,
    include_resolved: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoListResponse | EmptyTodoListResponse:
    """Get TODO items for an analysis.

    Args:
        analysis_id: ID of the analysis
        include_resolved: Whether to include resolved items (default: True)
        db: Database session
        current_user: Authenticated user

    Returns:
        TodoListResponse with items grouped by priority and category,
        or EmptyTodoListResponse if no items
    """
    # Verify analysis exists
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    # Query TODO items
    query = db.query(TodoItemModel).filter(TodoItemModel.analysis_id == analysis_id)

    if not include_resolved:
        query = query.filter(TodoItemModel.is_resolved == False)  # noqa: E712

    # Sort by priority (High first), then by category
    todo_models = query.order_by(
        TodoItemModel.priority,
        TodoItemModel.category,
        TodoItemModel.id,
    ).all()

    if not todo_models:
        return EmptyTodoListResponse()

    # Convert to Pydantic models
    items = [
        TodoItem(
            id=t.id,
            analysis_id=t.analysis_id,
            title=t.title,
            category=TodoCategory(t.category) if isinstance(t.category, str) else t.category,
            priority=TodoPriority(t.priority) if isinstance(t.priority, str) else t.priority,
            location=t.location or "",
            item_name=t.item_name,
            guidance=t.guidance or "",
            original_content=t.original_content,
            is_resolved=t.is_resolved,
            resolved_at=t.resolved_at,
            resolved_by=t.resolved_by_id,
            created_at=t.created_at,
        )
        for t in todo_models
    ]

    return TodoListResponse.from_items(items)


@router.get(
    "/{todo_id}",
    response_model=TodoItem,
    summary="Get a single TODO item",
    description="Retrieve details of a specific TODO item.",
)
async def get_todo_item(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoItem:
    """Get a single TODO item by ID.

    Args:
        todo_id: ID of the TODO item
        db: Database session
        current_user: Authenticated user

    Returns:
        TodoItem details
    """
    todo = db.query(TodoItemModel).filter(TodoItemModel.id == todo_id).first()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TODO item {todo_id} not found",
        )

    return TodoItem(
        id=todo.id,
        analysis_id=todo.analysis_id,
        title=todo.title,
        category=TodoCategory(todo.category) if isinstance(todo.category, str) else todo.category,
        priority=TodoPriority(todo.priority) if isinstance(todo.priority, str) else todo.priority,
        location=todo.location or "",
        item_name=todo.item_name,
        guidance=todo.guidance or "",
        original_content=todo.original_content,
        is_resolved=todo.is_resolved,
        resolved_at=todo.resolved_at,
        resolved_by=todo.resolved_by_id,
        created_at=todo.created_at,
    )


@router.patch(
    "/{todo_id}",
    response_model=TodoItem,
    summary="Update TODO item",
    description="Update a TODO item, typically to mark it as resolved or unresolved.",
)
async def update_todo_item(
    todo_id: int,
    update: TodoItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoItem:
    """Update a TODO item (mark resolved/unresolved).

    Args:
        todo_id: ID of the TODO item
        update: Update data
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated TodoItem
    """
    todo = db.query(TodoItemModel).filter(TodoItemModel.id == todo_id).first()
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TODO item {todo_id} not found",
        )

    # Update resolution status
    if update.is_resolved is not None:
        if update.is_resolved:
            todo.mark_resolved(user_id=current_user.id)
            logger.info(
                "TODO item %d marked as resolved by user %s",
                todo_id,
                current_user.username,
            )
        else:
            todo.mark_unresolved()
            logger.info(
                "TODO item %d marked as unresolved by user %s",
                todo_id,
                current_user.username,
            )

    db.commit()
    db.refresh(todo)

    return TodoItem(
        id=todo.id,
        analysis_id=todo.analysis_id,
        title=todo.title,
        category=TodoCategory(todo.category) if isinstance(todo.category, str) else todo.category,
        priority=TodoPriority(todo.priority) if isinstance(todo.priority, str) else todo.priority,
        location=todo.location or "",
        item_name=todo.item_name,
        guidance=todo.guidance or "",
        original_content=todo.original_content,
        is_resolved=todo.is_resolved,
        resolved_at=todo.resolved_at,
        resolved_by=todo.resolved_by_id,
        created_at=todo.created_at,
    )


@router.get(
    "/analysis/{analysis_id}/summary",
    response_model=TodoListSummary,
    summary="Get TODO list summary",
    description="Get summary counts for TODO items in an analysis.",
)
async def get_todo_summary(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoListSummary:
    """Get summary of TODO items for an analysis.

    Args:
        analysis_id: ID of the analysis
        db: Database session
        current_user: Authenticated user

    Returns:
        TodoListSummary with counts
    """
    # Verify analysis exists
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    # Query counts
    todos = (
        db.query(TodoItemModel).filter(TodoItemModel.analysis_id == analysis_id).all()
    )

    return TodoListSummary(
        total_count=len(todos),
        high_priority_count=sum(
            1 for t in todos if (t.priority == TodoPriority.HIGH or t.priority == "high")
        ),
        medium_priority_count=sum(
            1 for t in todos if (t.priority == TodoPriority.MEDIUM or t.priority == "medium")
        ),
        low_priority_count=sum(
            1 for t in todos if (t.priority == TodoPriority.LOW or t.priority == "low")
        ),
        resolved_count=sum(1 for t in todos if t.is_resolved),
        unresolved_count=sum(1 for t in todos if not t.is_resolved),
    )


@router.post(
    "/{todo_id}/resolve",
    response_model=TodoItem,
    summary="Mark TODO as resolved",
    description="Quick endpoint to mark a TODO item as resolved.",
)
async def resolve_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoItem:
    """Mark a TODO item as resolved.

    Args:
        todo_id: ID of the TODO item
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated TodoItem
    """
    return await update_todo_item(
        todo_id,
        TodoItemUpdate(is_resolved=True),
        db,
        current_user,
    )


@router.post(
    "/{todo_id}/unresolve",
    response_model=TodoItem,
    summary="Mark TODO as unresolved",
    description="Quick endpoint to mark a TODO item as unresolved.",
)
async def unresolve_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoItem:
    """Mark a TODO item as unresolved.

    Args:
        todo_id: ID of the TODO item
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated TodoItem
    """
    return await update_todo_item(
        todo_id,
        TodoItemUpdate(is_resolved=False),
        db,
        current_user,
    )
