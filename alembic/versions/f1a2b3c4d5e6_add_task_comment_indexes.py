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
    op.execute("DROP INDEX IF EXISTS ix_tasks_project_id")
    op.execute("DROP INDEX IF EXISTS ix_tasks_project_status")
    op.execute("DROP INDEX IF EXISTS ix_comments_task_id")
    op.execute("DROP INDEX IF EXISTS ix_comments_task_created")
    op.create_index(
        "ix_tasks_project_created_at_id",
        "tasks",
        ["project_id", "created_at", "id"],
    )
    op.create_index(
        "ix_comments_task_created_at_id",
        "comments",
        ["task_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_comments_task_created_at_id")
    op.execute("DROP INDEX IF EXISTS ix_tasks_project_created_at_id")
    op.execute("DROP INDEX IF EXISTS ix_comments_task_created")
    op.execute("DROP INDEX IF EXISTS ix_tasks_project_status")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_project_id ON tasks (project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_comments_task_id ON comments (task_id)")
