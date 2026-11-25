from typing import cast

from fastapi import APIRouter, status

from app.api.deps import (
    LabelEditor,
    LabelServiceDep,
    PaginationDep,
    ProjectEditor,
    ProjectViewer,
    TaskEditor,
)
from app.api.responses import RBAC_RESPONSES
from app.models.label import Label
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate
from app.schemas.page import PageResponse

router = APIRouter(tags=["labels"], responses=RBAC_RESPONSES)


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    payload: LabelCreate, access: ProjectEditor, service: LabelServiceDep
) -> Label:
    return await service.create(access, payload)


@router.get("/projects/{project_id}/labels", response_model=PageResponse[LabelRead])
async def list_labels(
    access: ProjectViewer, service: LabelServiceDep, pagination: PaginationDep
) -> PageResponse[LabelRead]:
    result = await service.list_labels(access, pagination)
    return PageResponse.from_result(
        cast(list[LabelRead], result.items), result.total, pagination.page, pagination.limit
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
