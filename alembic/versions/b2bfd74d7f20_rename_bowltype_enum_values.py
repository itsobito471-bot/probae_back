"""Rename BowlType enum values

Revision ID: b2bfd74d7f20
Revises: 236fb457d162
Create Date: 2026-08-23 22:06:46.414026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2bfd74d7f20'
down_revision: Union[str, Sequence[str], None] = '236fb457d162'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE bowltype RENAME VALUE 'STANDARD' TO 'BLOCK';")
    op.execute("ALTER TYPE bowltype RENAME VALUE 'CUSTOM' TO 'BLEND';")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE bowltype RENAME VALUE 'BLOCK' TO 'STANDARD';")
    op.execute("ALTER TYPE bowltype RENAME VALUE 'BLEND' TO 'CUSTOM';")
