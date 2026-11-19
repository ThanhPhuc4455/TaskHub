from dataclasses import dataclass

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.messages import PROJECT_ARCHIVED_MESSAGE
from app.core.pagination import Pagination
from app.models.enums import ProjectStatus, WorkspaceMemberRole
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.workspace_service import WorkspaceService


@dataclass(frozen=True)
class ProjectAccessContext:
    project: Project
    workspace: Workspace


class ProjectService:
    def __init__(self, projects: ProjectRepository, workspaces: WorkspaceService) -> None:
        self._projects = projects
        self._workspaces = workspaces

    async def create(self, access: Workspace, payload: ProjectCreate) -> Project:
        return await self._projects.create(
            workspace_id=access.id,
            name=payload.name,
            description=payload.description,
        )

    async def list_for_workspace(
        self, access: Workspace, pagination: Pagination
    ) -> tuple[list[Project], int]:
        return await self._projects.list_by_workspace(
            access.id, offset=pagination.offset, limit=pagination.limit
        )

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
        if access.project.status == ProjectStatus.ARCHIVED:
            raise BadRequestError(PROJECT_ARCHIVED_MESSAGE)
        data = payload.model_dump(exclude_unset=True)
        return await self._projects.update(access.project, data)

    async def archive(self, access: ProjectAccessContext) -> Project:
        if access.project.status == ProjectStatus.ARCHIVED:
            raise ConflictError(PROJECT_ARCHIVED_MESSAGE)
        return await self._projects.update(access.project, {"status": ProjectStatus.ARCHIVED})

    async def delete(self, access: ProjectAccessContext) -> None:
        await self._projects.delete(access.project)
