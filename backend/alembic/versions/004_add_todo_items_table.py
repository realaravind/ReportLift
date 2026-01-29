"""Add todo_items table for tracking manual work items.

Revision ID: 004
Revises: 003
Create Date: 2026-01-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create todo_items table."""
    op.create_table(
        "todo_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("item_name", sa.String(length=255), nullable=True),
        sa.Column("guidance", sa.Text(), nullable=True),
        sa.Column("original_content", sa.Text(), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, default=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_todo_items_analysis_id", "todo_items", ["analysis_id"])
    op.create_index("ix_todo_items_category", "todo_items", ["category"])
    op.create_index("ix_todo_items_priority", "todo_items", ["priority"])
    op.create_index("ix_todo_items_is_resolved", "todo_items", ["is_resolved"])


def downgrade() -> None:
    """Drop todo_items table."""
    op.drop_index("ix_todo_items_is_resolved", table_name="todo_items")
    op.drop_index("ix_todo_items_priority", table_name="todo_items")
    op.drop_index("ix_todo_items_category", table_name="todo_items")
    op.drop_index("ix_todo_items_analysis_id", table_name="todo_items")
    op.drop_table("todo_items")
