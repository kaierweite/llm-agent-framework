"""Add departments table and user-department association

Revision ID: 009_add_departments
Revises: 008_enhance_audit_logs
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "009_add_departments"
down_revision = "008_enhance_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 departments 表
    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("leader_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dept_parent_sort", "departments", ["parent_id", "sort_order"])

    # 2. users 表添加 department_id 外键
    op.add_column("users", sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True))

    # 3. 添加审计日志 action 常量对应的索引（已有 ix_audit_logs_action，无需重复）


def downgrade() -> None:
    op.drop_column("users", "department_id")
    op.drop_index("ix_dept_parent_sort", table_name="departments")
    op.drop_table("departments")
