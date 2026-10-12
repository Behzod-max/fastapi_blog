"""rename_content_to_body_in_posts

Revision ID: 7b5b70c42df1
Revises: e4a6b9c10b05
Create Date: 2026-10-06 00:48:56.762102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b5b70c42df1'
down_revision: Union[str, Sequence[str], None] = 'e4a6b9c10b05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'posts',
        'content',      # Eski nom
        new_column_name='body'   # Yangi nom
    )

def downgrade() -> None:
    op.alter_column(
        'posts',
        'body',
        new_column_name='content'
    )