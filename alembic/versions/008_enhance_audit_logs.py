"""Enhance audit logs with trace_id, user_agent, severity

Revision ID: 008_enhance_audit_logs
Revises: 007_add_tool_calls_to_messages
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "008_enhance_audit_logs"
down_revision = "007_add_tool_calls_to_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new columns to audit_logs
    op.add_column("audit_logs", sa.Column("trace_id", sa.String(12), nullable=True, index=True))
    op.add_column("audit_logs", sa.Column("user_agent", sa.String(500), nullable=True))
    op.add_column("audit_logs", sa.Column("severity", sa.String(10), nullable=False, server_default="INFO"))
    op.add_column("audit_logs", sa.Column("duration_ms", sa.Float, nullable=True))

    # 2. Make user_id nullable (for anonymous requests like failed logins)
    op.alter_column("audit_logs", "user_id", existing_type=sa.String(36), nullable=True)

    # 3. Widen user_email to handle longer emails
    op.alter_column("audit_logs", "user_email", existing_type=sa.String(255), nullable=True)

    # 4. Add composite index for severity + created_at (common dashboard query)
    op.create_index("ix_audit_logs_severity_created", "audit_logs", ["severity", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_severity_created", table_name="audit_logs")
    op.drop_column("audit_logs", "duration_ms")
    op.drop_column("audit_logs", "severity")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "trace_id")
