"""Add analyses and analysis_tasks tables.

Revision ID: 003
Revises: 002
Create Date: 2026-01-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create analyses and analysis_tasks tables."""
    # Create analyses table
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_path", sa.String(length=1000), nullable=False),
        sa.Column("report_name", sa.String(length=255), nullable=False),
        sa.Column("report_id", sa.String(length=255), nullable=True),
        sa.Column("classification", sa.String(length=50), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("penalties", sa.JSON(), nullable=True),
        sa.Column("todo_items", sa.JSON(), nullable=True),
        sa.Column("rdl_content", sa.Text(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyses_report_path", "analyses", ["report_path"])
    op.create_index("ix_analyses_analyzed_at", "analyses", ["analyzed_at"])

    # Create analysis_tasks table
    op.create_table(
        "analysis_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("report_path", sa.String(length=1000), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_tasks_task_id", "analysis_tasks", ["task_id"], unique=True)
    op.create_index("ix_analysis_tasks_status", "analysis_tasks", ["status"])


def downgrade() -> None:
    """Drop analyses and analysis_tasks tables."""
    op.drop_index("ix_analysis_tasks_status", table_name="analysis_tasks")
    op.drop_index("ix_analysis_tasks_task_id", table_name="analysis_tasks")
    op.drop_table("analysis_tasks")

    op.drop_index("ix_analyses_analyzed_at", table_name="analyses")
    op.drop_index("ix_analyses_report_path", table_name="analyses")
    op.drop_table("analyses")
