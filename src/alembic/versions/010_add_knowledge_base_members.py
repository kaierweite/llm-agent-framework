"""add knowledge base members table

Revision ID: 010_add_knowledge_base_members
Revises: 0b3ca239f839
Create Date: 2026-05-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010_add_knowledge_base_members'
down_revision: Union[str, None] = '0b3ca239f839'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create knowledge_base_members table
    op.create_table(
        'knowledge_base_members',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('knowledge_base_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('permission', sa.String(20), nullable=False, default='read'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('ix_kb_members_kb_id', 'knowledge_base_members', ['knowledge_base_id'])
    op.create_index('ix_kb_members_user_id', 'knowledge_base_members', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_kb_members_user_id', table_name='knowledge_base_members')
    op.drop_index('ix_kb_members_kb_id', table_name='knowledge_base_members')
    op.drop_table('knowledge_base_members')
