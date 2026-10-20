"""merge_chat_and_posts_heads

Revision ID: 9a1c3e5f7b2d
Revises: 0f28dfab5ae0, 2c4d6e8f0a1b
Create Date: 2026-10-21 01:15:00

"""
from typing import Sequence, Union


revision: str = "9a1c3e5f7b2d"
down_revision: Union[str, Sequence[str], None] = (
    "0f28dfab5ae0",
    "2c4d6e8f0a1b",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
