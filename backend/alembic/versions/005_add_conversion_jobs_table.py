"""Add conversion_jobs table.

Revision ID: 005
Revises: 004
Create Date: 2026-01-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create conversion_jobs table."""
    op.create_table(
        "conversion_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("report_path", sa.String(length=1000), nullable=False),
        sa.Column("report_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column("steps_completed", sa.Integer(), nullable=True),
        sa.Column("total_steps", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column("output_directory", sa.String(length=500), nullable=True),
        sa.Column("output_files", sa.JSON(), nullable=True),
        sa.Column("snowflake_configured", sa.Boolean(), nullable=True),
        sa.Column("snowflake_schema_used", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversion_jobs_job_id", "conversion_jobs", ["job_id"], unique=True)
    op.create_index("ix_conversion_jobs_status", "conversion_jobs", ["status"])
    op.create_index("ix_conversion_jobs_analysis_id", "conversion_jobs", ["analysis_id"])


def downgrade() -> None:
    """Drop conversion_jobs table."""
    op.drop_index("ix_conversion_jobs_analysis_id", table_name="conversion_jobs")
    op.drop_index("ix_conversion_jobs_status", table_name="conversion_jobs")
    op.drop_index("ix_conversion_jobs_job_id", table_name="conversion_jobs")
    op.drop_table("conversion_jobs")
