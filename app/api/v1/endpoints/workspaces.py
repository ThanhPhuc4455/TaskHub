from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PaginationDep, WorkspaceServiceDep
from app.api.responses import RBAC_RESPONSES
from app.models.workspace import Workspace
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspacePageResponse,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"], responses=RBAC_RESPONSES)


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, service: WorkspaceServiceDep, current_user: CurrentUser
) -> Workspace:
    return await service.create(payload, owner_id=current_user.id)


@router.get("", response_model=WorkspacePageResponse)
async def list_workspaces(
    service: WorkspaceServiceDep, current_user: CurrentUser, pagination: PaginationDep
) -> WorkspacePageResponse:
    result = await service.list_for_user(current_user, pagination)
    return WorkspacePageResponse(
        items=result.items, total=result.total, page=pagination.page, limit=pagination.limit
    )


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: int, service: WorkspaceServiceDep, current_user: CurrentUser
) -> Workspace:
    return await service.get(workspace_id, current_user)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    service: WorkspaceServiceDep,
    current_user: CurrentUser,
) -> Workspace:
    return await service.update(workspace_id, current_user, payload)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: int, service: WorkspaceServiceDep, current_user: CurrentUser
) -> None:
    await service.delete(workspace_id, current_user)
