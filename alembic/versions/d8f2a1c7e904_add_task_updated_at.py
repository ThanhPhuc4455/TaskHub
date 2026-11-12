"""add task updated_at timestamp

Revision ID: d8f2a1c7e904
Revises: c4f8a2d19e07
Create Date: 2026-11-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8f2a1c7e904"
down_revision: Union[str, Sequence[str], None] = "c4f8a2d19e07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tasks", "updated_at")
