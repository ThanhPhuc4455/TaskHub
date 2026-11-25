from dataclasses import dataclass

from app.core.cache import TaskCacheInvalidator
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.messages import FORBIDDEN_MESSAGE
from app.core.pagination import PageResult, Pagination
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceMemberRole
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


@dataclass(frozen=True)
class WorkspaceAccessContext:
    workspace: Workspace
    membership: WorkspaceMember | None
    effective_role: WorkspaceMemberRole


class WorkspaceService:
    def __init__(
        self,
        workspaces: WorkspaceRepository,
        members: WorkspaceMemberRepository,
        invalidator: TaskCacheInvalidator | None = None,
    ) -> None:
        self._workspaces = workspaces
        self._members = members
        self._invalidator = invalidator

    async def authorize(
        self, workspace_id: int, user: User, required: WorkspaceMemberRole
    ) -> Workspace:
        access = await self.authorize_context(workspace_id, user, required)
        return access.workspace

    async def authorize_context(
        self,
        workspace_id: int,
        user: User,
        required: WorkspaceMemberRole,
        *,
        workspace: Workspace | None = None,
    ) -> WorkspaceAccessContext:
        resolved_workspace = workspace or await self._workspaces.get(workspace_id)
        if resolved_workspace is None:
            raise NotFoundError("Workspace", workspace_id)
        if user.role == UserRole.ADMIN:
            return WorkspaceAccessContext(
                workspace=resolved_workspace,
                membership=None,
                effective_role=WorkspaceMemberRole.OWNER,
            )
        membership = await self._members.get_membership(workspace_id, user.id)
        if membership is None:
            raise NotFoundError("Workspace", workspace_id)
        if membership.role.rank < required.rank:
            raise ForbiddenError(FORBIDDEN_MESSAGE)
        return WorkspaceAccessContext(
            workspace=resolved_workspace,
            membership=membership,
            effective_role=membership.role,
        )

    async def require_role(
        self, workspace_id: int, user: User, required: WorkspaceMemberRole
    ) -> Workspace:
        return await self.authorize(workspace_id, user, required)

    async def create(self, payload: WorkspaceCreate, owner_id: int) -> Workspace:
        workspace = await self._workspaces.create(
            commit=False, name=payload.name, owner_id=owner_id
        )
        await self._members.create(
            commit=False,
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceMemberRole.OWNER,
        )
        await self._workspaces.commit()
        return workspace

    async def list_for_user(self, user: User, pagination: Pagination) -> PageResult[Workspace]:
        if user.role == UserRole.ADMIN:
            return await self._workspaces.get_page(pagination)
        return await self._workspaces.get_for_user(user.id, pagination)

    async def list_all(self, pagination: Pagination) -> PageResult[Workspace]:
        return await self._workspaces.get_page(pagination)

    async def get(self, workspace: Workspace) -> Workspace:
        return workspace

    async def update(self, workspace: Workspace, payload: WorkspaceUpdate) -> Workspace:
        data = payload.model_dump(exclude_unset=True)
        return await self._workspaces.update(workspace, data)

    async def delete(self, workspace: Workspace) -> None:
        project_ids = await self._workspaces.list_project_ids(workspace.id)
        await self._workspaces.delete(workspace)
        if self._invalidator is not None:
            for project_id in project_ids:
                await self._invalidator.invalidate(project_id)
