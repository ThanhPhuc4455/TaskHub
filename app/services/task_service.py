from dataclasses import dataclass

from app.core.exceptions import UnprocessableEntityError
from app.core.messages import ASSIGNEE_NOT_MEMBER_MESSAGE
from app.core.pagination import Pagination
from app.models.enums import WorkspaceMemberRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskFilters, TaskPage, TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project_policy import ensure_project_active
from app.services.project_service import ProjectAccessContext


@dataclass(frozen=True)
class TaskAccessContext:
    task: Task
    project: Project
    workspace: Workspace
    effective_role: WorkspaceMemberRole


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        projects: ProjectRepository,
        members: WorkspaceMemberRepository,
    ) -> None:
        self._tasks = tasks
        self._projects = projects
        self._members = members

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
    ) -> Task:
        ensure_project_active(access.project)
        await self._check_assignee(access.workspace.id, payload.assignee_id)
        task = await self._tasks.create(
            project_id=access.project.id,
            assignee_id=payload.assignee_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            due_date=payload.due_date,
            created_by=user.id,
        )
        return (await self._tasks.get_with_details(task.id)) or task

    async def list_tasks(
        self,
        access: ProjectAccessContext,
        filters: TaskFilters,
        pagination: Pagination,
    ) -> TaskPage:
        return await self._tasks.list_by_project(
            access.project.id,
            filters,
            pagination,
        )

    async def get(self, access: TaskAccessContext) -> Task:
        return access.task

    async def update(self, access: TaskAccessContext, payload: TaskUpdate) -> Task:
        ensure_project_active(access.project)
        data = payload.model_dump(exclude_unset=True)
        if "assignee_id" in data:
            await self._check_assignee(access.workspace.id, data["assignee_id"])
        return await self._tasks.update(access.task, data)

    async def delete(self, access: TaskAccessContext) -> None:
        ensure_project_active(access.project)
        await self._tasks.delete(access.task)
