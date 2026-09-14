"""add_order_window_settings

Revision ID: 999999999999
Revises: da1c41f61f94
Create Date: 2026-09-14 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '999999999999'
down_revision: Union[str, None] = 'da1c41f61f94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new values to the enum
    op.execute("ALTER TYPE settingkey ADD VALUE IF NOT EXISTS 'ORDER_WINDOW_START'")
    op.execute("ALTER TYPE settingkey ADD VALUE IF NOT EXISTS 'ORDER_WINDOW_END'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing values from ENUM types easily
    pass
