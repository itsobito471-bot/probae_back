"""add assembly status

Revision ID: 999999999998
Revises: 999999999999
Create Date: 2026-09-14 22:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '999999999998'
down_revision: Union[str, None] = '999999999999'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add assembly_status column to order_items as a string, default 'PENDING'
    op.add_column('order_items', sa.Column('assembly_status', sa.String(length=20), server_default='PENDING', nullable=False))


def downgrade() -> None:
    op.drop_column('order_items', 'assembly_status')
