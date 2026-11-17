import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.comment import Comment
from app.models.label import Label, task_labels
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace

REVIEW11_DATABASE_URL = os.environ["REVIEW11_DATABASE_URL"]


@pytest_asyncio.fixture
async def postgres_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(REVIEW11_DATABASE_URL, pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_task_and_project_cascade_children(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with postgres_sessionmaker() as session:
        owner = User(
            email=f"cascade-{uuid4().hex}@example.com",
            full_name="Cascade Owner",
            hashed_password="test-hash",
        )
        session.add(owner)
        await session.flush()
        workspace = Workspace(name=f"Cascade-{uuid4().hex}", owner_id=owner.id)
        session.add(workspace)
        await session.flush()
        project = Project(workspace_id=workspace.id, name="Cascade Project")
        session.add(project)
        await session.flush()
        task = Task(project_id=project.id, title="Cascade Task", created_by=owner.id)
        label = Label(project_id=project.id, name="cascade")
        session.add_all([task, label])
        await session.flush()
        await session.execute(insert(task_labels).values(task_id=task.id, label_id=label.id))
        session.add(Comment(task_id=task.id, author_id=owner.id, content="cascade"))
        await session.commit()
        task_id, project_id = task.id, project.id

        await session.delete(task)
        await session.commit()
        assert (
            await session.scalar(
                select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(task_labels)
                .where(task_labels.c.task_id == task_id)
            )
            == 0
        )

        await session.delete(project)
        await session.commit()
        assert (
            await session.scalar(
                select(func.count()).select_from(Label).where(Label.project_id == project_id)
            )
            == 0
        )
