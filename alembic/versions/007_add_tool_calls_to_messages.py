"""Add tool_calls column to messages table

Revision ID: 007_add_tool_calls_to_messages
Revises: 006_add_audit_logs_and_user_roles
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa

revision = "007_add_tool_calls_to_messages"
down_revision = "006_add_audit_logs_and_user_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("tool_calls", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "tool_calls")
