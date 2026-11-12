from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    CurrentUser,
    PaginationDep,
    TaskServiceDep,
    require_project_role,
    require_task_role,
)
from app.api.responses import RBAC_RESPONSES
from app.models.enums import TaskPriority, TaskStatus, WorkspaceMemberRole
from app.models.task import Task
from app.repositories.task_repository import TaskFilters
from app.schemas.task import TaskCreate, TaskPageResponse, TaskRead, TaskUpdate
from app.services.project_service import ProjectAccessContext
from app.services.task_service import TaskAccessContext

router = APIRouter(tags=["tasks"], responses=RBAC_RESPONSES)

ProjectViewer = Annotated[
    ProjectAccessContext,
    Depends(require_project_role(WorkspaceMemberRole.VIEWER)),
]
ProjectEditor = Annotated[
    ProjectAccessContext,
    Depends(require_project_role(WorkspaceMemberRole.EDITOR)),
]
TaskViewer = Annotated[
    TaskAccessContext,
    Depends(require_task_role(WorkspaceMemberRole.VIEWER)),
]
TaskEditor = Annotated[
    TaskAccessContext,
    Depends(require_task_role(WorkspaceMemberRole.EDITOR)),
]


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    payload: TaskCreate,
    access: ProjectEditor,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    return await service.create(access, current_user, payload)


@router.get("/projects/{project_id}/tasks", response_model=TaskPageResponse)
async def list_tasks(
    access: ProjectViewer,
    service: TaskServiceDep,
    pagination: PaginationDep,
    status_filter: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    priority: Annotated[list[TaskPriority] | None, Query()] = None,
    assignee_id: Annotated[int | None, Query(ge=1)] = None,
) -> TaskPageResponse:
    result = await service.list_tasks(
        access,
        TaskFilters(status=status_filter, priority=priority, assignee_id=assignee_id),
        pagination,
    )
    return TaskPageResponse(
        items=result.items, total=result.total, page=pagination.page, limit=pagination.limit
    )


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(access: TaskViewer, service: TaskServiceDep) -> Task:
    return await service.get(access)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(payload: TaskUpdate, access: TaskEditor, service: TaskServiceDep) -> Task:
    return await service.update(access, payload)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(access: TaskEditor, service: TaskServiceDep) -> None:
    await service.delete(access)
