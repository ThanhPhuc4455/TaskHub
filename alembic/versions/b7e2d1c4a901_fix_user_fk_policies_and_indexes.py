"""fix user foreign-key policies and add lookup indexes

Revision ID: b7e2d1c4a901
Revises: 969059663b7d
Create Date: 2026-11-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b7e2d1c4a901"
down_revision: Union[str, Sequence[str], None] = "969059663b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_constraint("comments_author_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_comments_author_id_users",
            "users",
            ["author_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_comments_author_id", ["author_id"], unique=False)

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("tasks_created_by_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_tasks_created_by_users",
            "users",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_tasks_created_by", ["created_by"], unique=False)

    with op.batch_alter_table("task_labels") as batch_op:
        batch_op.create_index("ix_task_labels_label_id", ["label_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("task_labels") as batch_op:
        batch_op.drop_index("ix_task_labels_label_id")

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_created_by")
        batch_op.drop_constraint("fk_tasks_created_by_users", type_="foreignkey")
        batch_op.create_foreign_key("tasks_created_by_fkey", "users", ["created_by"], ["id"])

    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_index("ix_comments_author_id")
        batch_op.drop_constraint("fk_comments_author_id_users", type_="foreignkey")
        batch_op.create_foreign_key("comments_author_id_fkey", "users", ["author_id"], ["id"])
