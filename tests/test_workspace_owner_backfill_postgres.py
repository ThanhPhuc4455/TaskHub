import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceMemberRole

REVIEW9_DATABASE_URL = os.getenv("REVIEW9_DATABASE_URL")


@pytest_asyncio.fixture
async def postgres_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    if not REVIEW9_DATABASE_URL:
        pytest.skip("REVIEW9_DATABASE_URL is required for PostgreSQL migration tests")
    engine = create_async_engine(REVIEW9_DATABASE_URL, pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_role", [WorkspaceMemberRole.VIEWER, WorkspaceMemberRole.EDITOR])
async def test_owner_backfill_upgrades_existing_membership_role(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
    existing_role: WorkspaceMemberRole,
) -> None:
    async with postgres_sessionmaker() as session:
        user = User(
            email=f"backfill-{uuid4().hex}@example.com",
            full_name="Backfill Owner",
            hashed_password="not-used",
        )
        session.add(user)
        await session.flush()
        workspace = Workspace(name=f"Backfill {uuid4().hex}", owner_id=user.id)
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role=existing_role,
            )
        )
        await session.commit()

        await session.execute(
            text(
                """
                INSERT INTO workspace_members (workspace_id, user_id, role)
                SELECT id, owner_id, 'OWNER' FROM workspaces WHERE id = :workspace_id
                ON CONFLICT (workspace_id, user_id)
                DO UPDATE SET role = 'OWNER'
                """
            ),
            {"workspace_id": workspace.id},
        )
        await session.commit()

        role = await session.scalar(
            select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
        )
        assert role == WorkspaceMemberRole.OWNER
