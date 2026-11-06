"""backfill workspace owner memberships

Revision ID: 969059663b7d
Revises: 5b266bf6275e
Create Date: 2026-11-06 12:18:04.593495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '969059663b7d'
down_revision: Union[str, Sequence[str], None] = '5b266bf6275e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO workspace_members (workspace_id, user_id, role)
        SELECT id, owner_id, 'OWNER' FROM workspaces
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    # The backfilled rows cannot be distinguished from later owner memberships.
    pass
