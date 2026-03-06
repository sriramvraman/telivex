"""add collected_at and reported_at to documents

Revision ID: a1f3c8d92e47
Revises: b533b484a72b
Create Date: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f3c8d92e47'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('collected_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('reported_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'reported_at')
    op.drop_column('documents', 'collected_at')
