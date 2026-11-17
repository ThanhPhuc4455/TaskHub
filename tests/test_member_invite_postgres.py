import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceMemberRole
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.member import InviteMemberRequest
from app.services.member_service import MemberService
from app.services.workspace_service import WorkspaceService

REVIEW9_DATABASE_URL = os.getenv("REVIEW9_DATABASE_URL")


@pytest_asyncio.fixture
async def postgres_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    if not REVIEW9_DATABASE_URL:
        pytest.skip("REVIEW9_DATABASE_URL is required for PostgreSQL member tests")
    engine = create_async_engine(REVIEW9_DATABASE_URL, pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def invite_once(
    sessionmaker: async_sessionmaker[AsyncSession], workspace_id: int, email: str
) -> str:
    async with sessionmaker() as session:
        service = MemberService(
            WorkspaceService(WorkspaceRepository(session), WorkspaceMemberRepository(session)),
            WorkspaceMemberRepository(session),
            UserRepository(session),
        )
        try:
            await service.invite(
                workspace_id,
                InviteMemberRequest(email=email, role=WorkspaceMemberRole.VIEWER),
            )
        except ConflictError:
            return "409"
        return "201"


@pytest.mark.asyncio
async def test_concurrent_invites_return_one_created_and_one_conflict(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    email = f"invitee-{uuid4().hex}@example.com"
    async with postgres_sessionmaker() as session:
        owner = User(
            email=f"owner-{uuid4().hex}@example.com",
            full_name="Owner",
            hashed_password=await hash_password("password123"),
        )
        invitee = User(
            email=email,
            full_name="Invitee",
            hashed_password=await hash_password("password123"),
        )
        session.add_all([owner, invitee])
        await session.flush()
        workspace = Workspace(name=f"Workspace-{uuid4().hex}", owner_id=owner.id)
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=owner.id,
                role=WorkspaceMemberRole.OWNER,
            )
        )
        await session.commit()
        workspace_id = workspace.id

    results = await asyncio.gather(
        invite_once(postgres_sessionmaker, workspace_id, email),
        invite_once(postgres_sessionmaker, workspace_id, email),
    )
    assert sorted(results) == ["201", "409"]

    async with postgres_sessionmaker() as session:
        memberships = list(
            (
                await session.scalars(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace_id,
                    )
                )
            ).all()
        )
        assert len(memberships) == 2
