"""Add audit_logs table and user roles

Revision ID: 006_add_audit_logs_and_user_roles
Revises: 005_add_user_avatar
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "006_add_audit_logs_and_user_roles"
down_revision = "005_add_user_avatar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add role column to users table
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))

    # 2. Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("user_email", sa.String(255), nullable=False),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # 3. Create composite index for common queries
    op.create_index("ix_audit_logs_action_user", "audit_logs", ["action", "user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # 4. Set existing admin user role (email = admin@llm-agent.local)
    op.execute("UPDATE users SET role = 'admin' WHERE email = 'admin@llm-agent.local'")


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_column("users", "role")
