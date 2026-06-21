"""add_ulid_to_all_tables

Revision ID: e6c654ca6a80
Revises: e6ec7ed32428
Create Date: 2026-06-21 14:59:44.798118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from ulid import ULID


# revision identifiers, used by Alembic.
revision: str = 'e6c654ca6a80'
down_revision: Union[str, Sequence[str], None] = 'e6ec7ed32428'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add columns as nullable=True
    op.add_column('audit_logs', sa.Column('ulid', sa.String(length=26), nullable=True))
    op.add_column('documents', sa.Column('ulid', sa.String(length=26), nullable=True))
    op.add_column('raw_materials', sa.Column('ulid', sa.String(length=26), nullable=True))
    op.add_column('users', sa.Column('ulid', sa.String(length=26), nullable=True))

    # 2. Populate ULIDs for existing rows
    connection = op.get_bind()
    for table_name in ['audit_logs', 'documents', 'raw_materials', 'users']:
        result = connection.execute(sa.text(f"SELECT id FROM {table_name}"))
        rows = result.fetchall()
        for row in rows:
            row_id = row[0]
            new_ulid = str(ULID())
            connection.execute(
                sa.text(f"UPDATE {table_name} SET ulid = :ulid WHERE id = :id"),
                {"ulid": new_ulid, "id": row_id}
            )

    # 3. Alter columns to be NOT NULL
    op.alter_column('audit_logs', 'ulid', nullable=False)
    op.alter_column('documents', 'ulid', nullable=False)
    op.alter_column('raw_materials', 'ulid', nullable=False)
    op.alter_column('users', 'ulid', nullable=False)

    # 4. Create unique indexes
    op.create_index(op.f('ix_audit_logs_ulid'), 'audit_logs', ['ulid'], unique=True)
    op.create_index(op.f('ix_documents_ulid'), 'documents', ['ulid'], unique=True)
    op.create_index(op.f('ix_raw_materials_ulid'), 'raw_materials', ['ulid'], unique=True)
    op.create_index(op.f('ix_users_ulid'), 'users', ['ulid'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_ulid'), table_name='users')
    op.drop_column('users', 'ulid')
    op.drop_index(op.f('ix_raw_materials_ulid'), table_name='raw_materials')
    op.drop_column('raw_materials', 'ulid')
    op.drop_index(op.f('ix_documents_ulid'), table_name='documents')
    op.drop_column('documents', 'ulid')
    op.drop_index(op.f('ix_audit_logs_ulid'), table_name='audit_logs')
    op.drop_column('audit_logs', 'ulid')
