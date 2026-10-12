"""rename_content_to_body_in_posts

Revision ID: 0f28dfab5ae0
Revises: 7b5b70c42df1
Create Date: 2026-10-06 00:49:46.646276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f28dfab5ae0'
down_revision: Union[str, Sequence[str], None] = '7b5b70c42df1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
