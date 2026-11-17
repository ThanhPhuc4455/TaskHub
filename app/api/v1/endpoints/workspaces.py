from typing import cast

from fastapi import APIRouter, status

from app.api.deps import (
    CacheDep,
    CurrentUser,
    PaginationDep,
    WorkspaceOwner,
    WorkspaceServiceDep,
    WorkspaceViewer,
)
from app.api.responses import RBAC_RESPONSES
from app.core.cache import invalidate_task_cache
from app.models.workspace import Workspace
from app.schemas.page import PageResponse
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"], responses=RBAC_RESPONSES)


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, service: WorkspaceServiceDep, current_user: CurrentUser
) -> Workspace:
    return await service.create(payload, owner_id=current_user.id)


@router.get("", response_model=PageResponse[WorkspaceRead])
async def list_workspaces(
    service: WorkspaceServiceDep, current_user: CurrentUser, pagination: PaginationDep
) -> PageResponse[WorkspaceRead]:
    items, total = await service.list_for_user(current_user, pagination)
    return PageResponse.from_result(
        cast(list[WorkspaceRead], items), total, pagination.page, pagination.limit
    )


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(workspace: WorkspaceViewer, service: WorkspaceServiceDep) -> Workspace:
    return await service.get(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    payload: WorkspaceUpdate,
    service: WorkspaceServiceDep,
    workspace: WorkspaceOwner,
) -> Workspace:
    return await service.update(workspace, payload)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    service: WorkspaceServiceDep,
    workspace: WorkspaceOwner,
    current_user: CurrentUser,
    cache: CacheDep,
) -> None:
    project_ids = await service.project_ids(workspace.id, current_user)
    await service.delete(workspace)
    for project_id in project_ids:
        await invalidate_task_cache(cache, project_id)
