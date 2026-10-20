"""add_chat_messages_and_user_avatars

Revision ID: 2c4d6e8f0a1b
Revises: e4a6b9c10b05
Create Date: 2026-10-21 01:12:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2c4d6e8f0a1b"
down_revision: Union[str, Sequence[str], None] = "e4a6b9c10b05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=255), nullable=True))
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room", sa.String(length=100), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_room", "messages", ["room"], unique=False)
    op.create_index("ix_messages_created_at", "messages", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_room", table_name="messages")
    op.drop_table("messages")
    op.drop_column("users", "avatar_url")
