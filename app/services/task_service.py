import logging
from dataclasses import dataclass

from app.core.cache import (
    CACHE_BACKEND_ERRORS,
    CacheBackend,
    invalidate_task_cache,
    read_task_cache,
    write_task_cache,
)
from app.core.exceptions import UnprocessableEntityError
from app.core.messages import ASSIGNEE_NOT_MEMBER_MESSAGE
from app.core.pagination import Pagination
from app.models.enums import TaskStatus, WorkspaceMemberRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskFilters, TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.page import PageResponse
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.project_policy import ensure_project_active
from app.services.project_service import ProjectAccessContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskAccessContext:
    task: Task
    project: Project
    workspace: Workspace
    effective_role: WorkspaceMemberRole


@dataclass(frozen=True)
class TaskMutationResult:
    task: Task
    should_notify_assignee: bool


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        projects: ProjectRepository,
        members: WorkspaceMemberRepository,
        cache: CacheBackend | None = None,
    ) -> None:
        self._tasks = tasks
        self._projects = projects
        self._members = members
        self._cache = cache

    async def _list_from_database(
        self, access: ProjectAccessContext, filters: TaskFilters, pagination: Pagination
    ) -> PageResponse[TaskRead]:
        result = await self._tasks.list_by_project(access.project.id, filters, pagination)
        return PageResponse.from_result(
            [TaskRead.model_validate(item) for item in result.items],
            result.total,
            pagination.page,
            pagination.limit,
        )

    async def _invalidate(self, project_id: int) -> None:
        if self._cache is not None:
            await invalidate_task_cache(self._cache, project_id)

    async def _check_assignee(self, workspace_id: int, assignee_id: int | None) -> None:
        if (
            assignee_id is not None
            and await self._members.get_membership(workspace_id, assignee_id) is None
        ):
            raise UnprocessableEntityError(ASSIGNEE_NOT_MEMBER_MESSAGE)

    async def create(
        self,
        access: ProjectAccessContext,
        user: User,
        payload: TaskCreate,
    ) -> TaskMutationResult:
        ensure_project_active(access.project)
        await self._check_assignee(access.workspace.id, payload.assignee_id)
        task = await self._tasks.create(
            project_id=access.project.id,
            assignee_id=payload.assignee_id,
            title=payload.title,
            description=payload.description,
            status=TaskStatus.TODO,
            priority=payload.priority,
            due_date=payload.due_date,
            created_by=user.id,
        )
        await self._invalidate(access.project.id)
        task = (await self._tasks.get_with_details(task.id)) or task
        return TaskMutationResult(
            task=task,
            should_notify_assignee=task.assignee is not None and task.assignee.id != user.id,
        )

    async def list_tasks(
        self,
        access: ProjectAccessContext,
        filters: TaskFilters,
        pagination: Pagination,
    ) -> PageResponse[TaskRead]:
        if self._cache is None:
            return await self._list_from_database(access, filters, pagination)
        cache_key: str | None = None
        try:
            cache_key, cached = await read_task_cache(
                self._cache, access.project.id, filters, pagination
            )
            if cached is not None:
                return PageResponse[TaskRead].model_validate_json(cached)
        except CACHE_BACKEND_ERRORS:
            logger.warning(
                "Task cache read failed for project_id=%s", access.project.id, exc_info=True
            )
        response = await self._list_from_database(access, filters, pagination)
        if cache_key is not None:
            try:
                await write_task_cache(self._cache, cache_key, response.model_dump_json())
            except CACHE_BACKEND_ERRORS:
                logger.warning(
                    "Task cache write failed for project_id=%s", access.project.id, exc_info=True
                )
        return response

    async def get(self, access: TaskAccessContext) -> Task:
        return access.task

    async def update(
        self, access: TaskAccessContext, user: User, payload: TaskUpdate
    ) -> TaskMutationResult:
        ensure_project_active(access.project)
        previous_assignee_id = access.task.assignee_id
        data = payload.model_dump(exclude_unset=True)
        if "assignee_id" in data:
            await self._check_assignee(access.workspace.id, data["assignee_id"])
        updated = await self._tasks.update(access.task, data)
        await self._invalidate(access.project.id)
        updated = (await self._tasks.get_with_details(updated.id)) or updated
        return TaskMutationResult(
            task=updated,
            should_notify_assignee=(
                "assignee_id" in payload.model_fields_set
                and updated.assignee is not None
                and updated.assignee.id != previous_assignee_id
                and updated.assignee.id != user.id
            ),
        )

    async def delete(self, access: TaskAccessContext) -> None:
        ensure_project_active(access.project)
        await self._tasks.delete(access.task)
        await self._invalidate(access.project.id)
