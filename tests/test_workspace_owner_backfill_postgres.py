import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceMemberRole

REVIEW9_MIGRATION_DATABASE_URL = os.getenv("REVIEW9_MIGRATION_DATABASE_URL")


def run_alembic(database_url: str, revision: str) -> None:
    previous_url = settings.database_url
    settings.database_url = database_url
    try:
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        command.upgrade(config, revision)
    finally:
        settings.database_url = previous_url


async def migrate(database_url: str, revision: str) -> None:
    await asyncio.to_thread(run_alembic, database_url, revision)


@pytest_asyncio.fixture
async def postgres_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    if not REVIEW9_MIGRATION_DATABASE_URL:
        pytest.skip(
            "REVIEW9_MIGRATION_DATABASE_URL is required for PostgreSQL migration tests"
        )
    await migrate(REVIEW9_MIGRATION_DATABASE_URL, "base")
    await migrate(REVIEW9_MIGRATION_DATABASE_URL, "5b266bf6275e")
    engine = create_async_engine(REVIEW9_MIGRATION_DATABASE_URL, pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_owner_backfill_promotes_existing_and_creates_missing_memberships(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_sessionmaker() as session:
        owner_with_membership = User(
            email=f"owner-existing-{uuid4().hex}@example.com",
            full_name="Existing Owner",
            hashed_password="not-used",
        )
        owner_without_membership = User(
            email=f"owner-missing-{uuid4().hex}@example.com",
            full_name="Missing Owner",
            hashed_password="not-used",
        )
        non_owner = User(
            email=f"member-{uuid4().hex}@example.com",
            full_name="Non Owner",
            hashed_password="not-used",
        )
        session.add_all([owner_with_membership, owner_without_membership, non_owner])
        await session.flush()

        workspace_with_membership = Workspace(
            name=f"Existing {uuid4().hex}", owner_id=owner_with_membership.id
        )
        workspace_without_membership = Workspace(
            name=f"Missing {uuid4().hex}", owner_id=owner_without_membership.id
        )
        session.add_all([workspace_with_membership, workspace_without_membership])
        await session.flush()
        session.add_all(
            [
                WorkspaceMember(
                    workspace_id=workspace_with_membership.id,
                    user_id=owner_with_membership.id,
                    role=WorkspaceMemberRole.VIEWER,
                ),
                WorkspaceMember(
                    workspace_id=workspace_with_membership.id,
                    user_id=non_owner.id,
                    role=WorkspaceMemberRole.EDITOR,
                ),
            ]
        )
        await session.commit()

    await migrate(REVIEW9_MIGRATION_DATABASE_URL, "969059663b7d")  # type: ignore[arg-type]

    async with postgres_sessionmaker() as session:
        memberships = list(
            (
                await session.scalars(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace_with_membership.id
                    )
                )
            ).all()
        )
        roles = {(membership.user_id, membership.role) for membership in memberships}
        assert (owner_with_membership.id, WorkspaceMemberRole.OWNER) in roles
        assert (non_owner.id, WorkspaceMemberRole.EDITOR) in roles

        owner_membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_without_membership.id,
                WorkspaceMember.user_id == owner_without_membership.id,
            )
        )
        assert owner_membership is not None
        assert owner_membership.role == WorkspaceMemberRole.OWNER
