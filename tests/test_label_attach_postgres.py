import asyncio
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.task_repository import TaskRepository

REVIEW11_DATABASE_URL = os.environ["REVIEW11_DATABASE_URL"]


@pytest_asyncio.fixture
async def postgres_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(REVIEW11_DATABASE_URL, pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def attach_once(
    sessionmaker: async_sessionmaker[AsyncSession],
    task_id: int,
    label_id: int,
    barrier: asyncio.Barrier,
) -> int:
    async with sessionmaker() as session:
        await barrier.wait()
        return await TaskRepository(session).attach_label(task_id, label_id)


@pytest.mark.asyncio
async def test_concurrent_attach_returns_one_insert_and_one_noop(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_sessionmaker() as session:
        owner = User(
            email=f"label-{uuid4().hex}@example.com",
            full_name="Label Owner",
            hashed_password="test-hash",
        )
        session.add(owner)
        await session.flush()
        workspace = Workspace(name=f"Labels-{uuid4().hex}", owner_id=owner.id)
        session.add(workspace)
        await session.flush()
        project = Project(workspace_id=workspace.id, name="Labels Project")
        session.add(project)
        await session.flush()
        task = Task(project_id=project.id, title="Task", created_by=owner.id)
        label = Label(project_id=project.id, name="backend")
        session.add_all([task, label])
        await session.commit()
        task_id, label_id = task.id, label.id

    barrier = asyncio.Barrier(2)
    results = await asyncio.gather(
        attach_once(postgres_sessionmaker, task_id, label_id, barrier),
        attach_once(postgres_sessionmaker, task_id, label_id, barrier),
    )
    assert sorted(results) == [0, 1]

    async with postgres_sessionmaker() as session:
        await session.execute(delete(Project).where(Project.id == project.id))
        await session.commit()
