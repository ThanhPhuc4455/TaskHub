"""add check constraints for string-backed enums

Revision ID: c4f8a2d19e07
Revises: b7e2d1c4a901
Create Date: 2026-11-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c4f8a2d19e07"
down_revision: Union[str, Sequence[str], None] = "b7e2d1c4a901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "user_role",
        "users",
        "role IN ('ADMIN', 'MEMBER')",
    )
    op.create_check_constraint(
        "workspace_member_role",
        "workspace_members",
        "role IN ('OWNER', 'EDITOR', 'VIEWER')",
    )
    op.create_check_constraint(
        "project_status",
        "projects",
        "status IN ('ACTIVE', 'ARCHIVED')",
    )
    op.create_check_constraint(
        "task_status",
        "tasks",
        "status IN ('TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE')",
    )
    op.create_check_constraint(
        "task_priority",
        "tasks",
        "priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')",
    )


def downgrade() -> None:
    op.drop_constraint("task_priority", "tasks", type_="check")
    op.drop_constraint("task_status", "tasks", type_="check")
    op.drop_constraint("project_status", "projects", type_="check")
    op.drop_constraint("workspace_member_role", "workspace_members", type_="check")
    op.drop_constraint("user_role", "users", type_="check")
