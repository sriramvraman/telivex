"""add users table and user_id to documents

Revision ID: 003
Revises: a1f3c8d92e47
Create Date: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = 'a1f3c8d92e47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.add_column('documents', sa.Column('user_id', sa.String(36), nullable=True))
    op.create_foreign_key('fk_documents_user_id', 'documents', 'users', ['user_id'], ['user_id'])
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_documents_user_id', table_name='documents')
    op.drop_constraint('fk_documents_user_id', 'documents', type_='foreignkey')
    op.drop_column('documents', 'user_id')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
