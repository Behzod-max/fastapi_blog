"""add_phone_to_users

Revision ID: e4a6b9c10b05
Revises: 9ceec9707972
Create Date: 2026-10-05 15:59:39.573463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a6b9c10b05'
down_revision: Union[str, Sequence[str], None] = '9ceec9707972'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.create_index('ix_users_phone', 'users', ['phone'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_users_phone', table_name='users')
    op.drop_column('users', 'phone')
