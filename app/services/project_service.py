from dataclasses import dataclass

from app.core.cache import CacheBackend, invalidate_task_cache
from app.core.exceptions import ConflictError, NotFoundError
from app.core.messages import PROJECT_ARCHIVED_MESSAGE
from app.core.pagination import PageResult, Pagination
from app.models.enums import ProjectStatus, WorkspaceMemberRole
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project_policy import ensure_project_active
from app.services.workspace_service import WorkspaceService


@dataclass(frozen=True)
class ProjectAccessContext:
    project: Project
    workspace: Workspace
    membership: WorkspaceMember | None
    effective_role: WorkspaceMemberRole


class ProjectService:
    def __init__(
        self,
        projects: ProjectRepository,
        workspaces: WorkspaceService,
        cache: CacheBackend | None = None,
    ) -> None:
        self._projects = projects
        self._workspaces = workspaces
        self._cache = cache

    async def _invalidate(self, project_id: int) -> None:
        if self._cache is not None:
            await invalidate_task_cache(self._cache, project_id)

    async def create(self, access: Workspace, payload: ProjectCreate) -> Project:
        return await self._projects.create(
            workspace_id=access.id,
            name=payload.name,
            description=payload.description,
        )

    async def list_for_workspace(
        self, access: Workspace, pagination: Pagination
    ) -> PageResult[Project]:
        return await self._projects.list_by_workspace(access.id, pagination)

    async def require_project_role(
        self, project_id: int, user: User, required: WorkspaceMemberRole
    ) -> ProjectAccessContext:
        project = await self._projects.get_with_workspace(project_id)
        if project is None:
            raise NotFoundError("Project", project_id)
        access = await self._workspaces.authorize_context(project.workspace_id, user, required)
        return ProjectAccessContext(
            project=project,
            workspace=access.workspace,
            membership=access.membership,
            effective_role=access.effective_role,
        )

    async def get(self, access: ProjectAccessContext) -> Project:
        return access.project

    async def update(self, access: ProjectAccessContext, payload: ProjectUpdate) -> Project:
        ensure_project_active(access.project)
        data = payload.model_dump(exclude_unset=True)
        return await self._projects.update(access.project, data)

    async def archive(self, access: ProjectAccessContext) -> Project:
        if access.project.status == ProjectStatus.ARCHIVED:
            raise ConflictError(PROJECT_ARCHIVED_MESSAGE)
        project = await self._projects.update(access.project, {"status": ProjectStatus.ARCHIVED})
        await self._invalidate(project.id)
        return project

    async def unarchive(self, access: ProjectAccessContext) -> Project:
        project = await self._projects.update(access.project, {"status": ProjectStatus.ACTIVE})
        await self._invalidate(project.id)
        return project

    async def delete(self, access: ProjectAccessContext) -> None:
        await self._projects.delete(access.project)
        await self._invalidate(access.project.id)
