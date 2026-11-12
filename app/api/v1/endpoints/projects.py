from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    PaginationDep,
    ProjectServiceDep,
    require_project_role,
    require_workspace_role,
)
from app.api.responses import RBAC_RESPONSES
from app.models.enums import WorkspaceMemberRole
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectAccessContext
from app.services.workspace_service import WorkspaceAccessContext

router = APIRouter(tags=["projects"], responses=RBAC_RESPONSES)

WorkspaceViewer = Annotated[
    WorkspaceAccessContext,
    Depends(require_workspace_role(WorkspaceMemberRole.VIEWER)),
]
WorkspaceEditor = Annotated[
    WorkspaceAccessContext,
    Depends(require_workspace_role(WorkspaceMemberRole.EDITOR)),
]
ProjectViewer = Annotated[
    ProjectAccessContext,
    Depends(require_project_role(WorkspaceMemberRole.VIEWER)),
]
ProjectEditor = Annotated[
    ProjectAccessContext,
    Depends(require_project_role(WorkspaceMemberRole.EDITOR)),
]
ProjectOwner = Annotated[
    ProjectAccessContext,
    Depends(require_project_role(WorkspaceMemberRole.OWNER)),
]


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreate,
    access: WorkspaceEditor,
    service: ProjectServiceDep,
) -> Project:
    return await service.create(access, payload)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=list[ProjectRead],
    summary="List workspace projects",
)
async def list_projects(
    access: WorkspaceViewer,
    service: ProjectServiceDep,
    pagination: PaginationDep,
) -> list[Project]:
    return await service.list_for_workspace(access, pagination)


@router.get("/projects/{project_id}", response_model=ProjectRead, summary="Get a project")
async def get_project(access: ProjectViewer, service: ProjectServiceDep) -> Project:
    return await service.get(access)


@router.patch("/projects/{project_id}", response_model=ProjectRead, summary="Update a project")
async def update_project(
    payload: ProjectUpdate,
    access: ProjectEditor,
    service: ProjectServiceDep,
) -> Project:
    return await service.update(access, payload)


@router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectRead,
    summary="Archive a project",
)
async def archive_project(access: ProjectOwner, service: ProjectServiceDep) -> Project:
    return await service.archive(access)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(access: ProjectOwner, service: ProjectServiceDep) -> None:
    await service.delete(access)
