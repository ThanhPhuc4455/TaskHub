from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import Pagination
from app.models.label import task_labels
from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class TaskFilters:
    status: list[TaskStatus] | None = None
    priority: list[TaskPriority] | None = None
    assignee_id: int | None = None


@dataclass(frozen=True)
class TaskPage:
    items: list[Task]
    total: int


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Task)

    def _where(self, project_id: int, filters: TaskFilters) -> list[Any]:
        conditions = [Task.project_id == project_id]
        if filters.status:
            conditions.append(Task.status.in_(filters.status))
        if filters.priority:
            conditions.append(Task.priority.in_(filters.priority))
        if filters.assignee_id is not None:
            conditions.append(Task.assignee_id == filters.assignee_id)
        return conditions

    async def get_with_details(self, task_id: int) -> Task | None:
        return await self.session.scalar(
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.labels), selectinload(Task.assignee))
        )

    async def list_by_project(
        self, project_id: int, filters: TaskFilters, pagination: Pagination
    ) -> TaskPage:
        conditions = self._where(project_id, filters)
        total = await self.session.scalar(select(func.count()).select_from(Task).where(*conditions))
        stmt = (
            select(Task)
            .where(*conditions)
            .options(selectinload(Task.labels), selectinload(Task.assignee))
            .order_by(Task.created_at.desc(), Task.id.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.scalars(stmt)
        return TaskPage(items=list(result.all()), total=total or 0)

    async def attach_label(self, task_id: int, label_id: int, *, commit: bool = True) -> None:
        await self.session.execute(insert(task_labels).values(task_id=task_id, label_id=label_id))
        await self._flush_or_commit(commit)

    async def detach_label(self, task_id: int, label_id: int, *, commit: bool = True) -> int:
        result = await self.session.execute(
            delete(task_labels).where(
                task_labels.c.task_id == task_id,
                task_labels.c.label_id == label_id,
            )
        )
        await self._flush_or_commit(commit)
        return int(getattr(result, "rowcount", 0) or 0)
