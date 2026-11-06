from fastapi import APIRouter, status

from app.api.deps import CurrentUser, WorkspaceServiceDep
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate, service: WorkspaceServiceDep, current_user: CurrentUser
) -> Workspace:
    return await service.create(payload, owner_id=current_user.id)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    service: WorkspaceServiceDep, current_user: CurrentUser
) -> list[Workspace]:
    return await service.list_for_user(current_user)


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
