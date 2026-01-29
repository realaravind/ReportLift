"""Add audit_logs table.

Revision ID: 006
Revises: 005
Create Date: 2026-01-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_logs table with indexes for query performance."""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "event_type IN ('LOGIN', 'LOGOUT', 'ANALYSIS', 'CONVERSION', 'CONFIG_CHANGE')",
            name="chk_event_type",
        ),
        sa.CheckConstraint(
            "status IN ('SUCCESS', 'FAILURE')",
            name="chk_status",
        ),
    )

    # Indexes for efficient querying
    op.create_index("idx_audit_logs_timestamp", "audit_logs", ["timestamp"], postgresql_using="btree")
    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("idx_audit_logs_user_timestamp", "audit_logs", ["user_id", "timestamp"])


def downgrade() -> None:
    """Drop audit_logs table and indexes."""
    op.drop_index("idx_audit_logs_user_timestamp", table_name="audit_logs")
    op.drop_index("idx_audit_logs_event_type", table_name="audit_logs")
    op.drop_index("idx_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")
