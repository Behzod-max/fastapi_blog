"""recognize the existing database revision

Revision ID: f142721e8624
Revises: 0f28dfab5ae0
"""
from typing import Sequence, Union


revision: str = "f142721e8624"
down_revision: Union[str, Sequence[str], None] = "0f28dfab5ae0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
