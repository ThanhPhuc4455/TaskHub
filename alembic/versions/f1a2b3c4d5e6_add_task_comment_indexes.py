"""add task and comment composite indexes

Revision ID: f1a2b3c4d5e6
Revises: d8f2a1c7e904
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "d8f2a1c7e904"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_tasks_project_status", "tasks", ["project_id", "status"])
    op.create_index("ix_comments_task_created", "comments", ["task_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_comments_task_created", table_name="comments")
    op.drop_index("ix_tasks_project_status", table_name="tasks")
