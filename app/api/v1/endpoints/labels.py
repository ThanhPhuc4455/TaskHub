from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    LabelServiceDep,
    PaginationDep,
    require_label_role,
    require_project_role,
    require_task_role,
)
from app.api.responses import RBAC_RESPONSES
from app.models.enums import WorkspaceMemberRole
from app.models.label import Label
from app.schemas.label import LabelCreate, LabelPageResponse, LabelRead, LabelUpdate
from app.services.label_service import LabelAccessContext
from app.services.project_service import ProjectAccessContext
from app.services.task_service import TaskAccessContext

router = APIRouter(tags=["labels"], responses=RBAC_RESPONSES)

ProjectViewer = Annotated[
    ProjectAccessContext,
    Depends(require_project_role(WorkspaceMemberRole.VIEWER)),
]
ProjectEditor = Annotated[
    ProjectAccessContext,
    Depends(require_project_role(WorkspaceMemberRole.EDITOR)),
]
TaskEditor = Annotated[
    TaskAccessContext,
    Depends(require_task_role(WorkspaceMemberRole.EDITOR)),
]
LabelEditor = Annotated[
    LabelAccessContext,
    Depends(require_label_role(WorkspaceMemberRole.EDITOR)),
]


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    payload: LabelCreate, access: ProjectEditor, service: LabelServiceDep
) -> Label:
    return await service.create(access, payload)


@router.get("/projects/{project_id}/labels", response_model=LabelPageResponse)
async def list_labels(
    access: ProjectViewer, service: LabelServiceDep, pagination: PaginationDep
) -> LabelPageResponse:
    result = await service.list_labels(access, pagination)
    return LabelPageResponse(
        items=result.items, total=result.total, page=pagination.page, limit=pagination.limit
    )


@router.patch("/labels/{label_id}", response_model=LabelRead)
async def update_label(
    payload: LabelUpdate, access: LabelEditor, service: LabelServiceDep
) -> Label:
    return await service.update(access, payload)


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(access: LabelEditor, service: LabelServiceDep) -> None:
    await service.delete(access)


@router.post("/tasks/{task_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def attach_label(
    task: TaskEditor,
    label_id: int,
    service: LabelServiceDep,
) -> None:
    await service.attach(task, label_id)


@router.delete("/tasks/{task_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_label(
    task: TaskEditor,
    label_id: int,
    service: LabelServiceDep,
) -> None:
    await service.detach(task, label_id)
