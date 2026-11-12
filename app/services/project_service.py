from dataclasses import dataclass

from app.core.exceptions import NotFoundError
from app.core.pagination import PageResult, Pagination
from app.models.enums import ProjectStatus, WorkspaceMemberRole
from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.policies import ensure_project_active
from app.services.workspace_service import WorkspaceAccessContext, WorkspaceService


@dataclass(frozen=True)
class ProjectAccessContext:
    project: Project
    workspace: WorkspaceAccessContext


class ProjectService:
    def __init__(self, projects: ProjectRepository, workspaces: WorkspaceService) -> None:
        self._projects = projects
        self._workspaces = workspaces

    async def create(self, access: WorkspaceAccessContext, payload: ProjectCreate) -> Project:
        return await self._projects.create(
            workspace_id=access.workspace_id,
            name=payload.name,
            description=payload.description,
        )

    async def list_for_workspace(
        self, access: WorkspaceAccessContext, pagination: Pagination
    ) -> PageResult[Project]:
        return await self._projects.list_by_workspace(access.workspace_id, pagination)

    async def require_project_role(
        self, project_id: int, user: User, required: WorkspaceMemberRole
    ) -> ProjectAccessContext:
        project = await self._projects.get(project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        workspace = await self._workspaces.authorize(project.workspace_id, user, required)
        return ProjectAccessContext(project=project, workspace=workspace)

    async def get(self, access: ProjectAccessContext) -> Project:
        return access.project

    async def update(self, access: ProjectAccessContext, payload: ProjectUpdate) -> Project:
        ensure_project_active(access.project)
        data = payload.model_dump(exclude_unset=True)
        return await self._projects.update(access.project, data)

    async def archive(self, access: ProjectAccessContext) -> Project:
        return await self._projects.update(access.project, {"status": ProjectStatus.ARCHIVED})

    async def unarchive(self, access: ProjectAccessContext) -> Project:
        return await self._projects.update(access.project, {"status": ProjectStatus.ACTIVE})

    async def delete(self, access: ProjectAccessContext) -> None:
        await self._projects.delete(access.project)
