from dataclasses import dataclass

from app.core.constants import FORBIDDEN_MESSAGE
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.pagination import PageResult, Pagination
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMemberRole
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


@dataclass(frozen=True)
class WorkspaceAccessContext:
    workspace_id: int
    user: User
    effective_role: WorkspaceMemberRole
    workspace: Workspace


async def authorize_resource[ResourceT](
    resource: ResourceT | None,
    resource_name: str,
    workspace_id: int,
    user: User,
    required: WorkspaceMemberRole,
    service: "WorkspaceService",
) -> tuple[ResourceT, WorkspaceAccessContext]:
    if resource is None:
        raise NotFoundError(resource_name, workspace_id)
    access = await service.authorize(workspace_id, user, required)
    return resource, access


class WorkspaceService:
    def __init__(self, workspaces: WorkspaceRepository, members: WorkspaceMemberRepository) -> None:
        self._workspaces = workspaces
        self._members = members

    async def authorize(
        self, workspace_id: int, user: User, required: WorkspaceMemberRole
    ) -> WorkspaceAccessContext:
        workspace = await self._workspaces.get(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", workspace_id)
        if user.role == UserRole.ADMIN:
            return WorkspaceAccessContext(
                workspace_id=workspace_id,
                user=user,
                effective_role=WorkspaceMemberRole.OWNER,
                workspace=workspace,
            )
        membership = await self._members.get_membership(workspace_id, user.id)
        if membership is None:
            raise NotFoundError("Workspace", workspace_id)
        if membership.role.rank < required.rank:
            raise ForbiddenError(FORBIDDEN_MESSAGE)
        return WorkspaceAccessContext(
            workspace_id=workspace_id,
            user=user,
            effective_role=membership.role,
            workspace=workspace,
        )

    async def require_role(
        self, workspace_id: int, user: User, required: WorkspaceMemberRole
    ) -> Workspace:
        return (await self.authorize(workspace_id, user, required)).workspace

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

    async def get(self, workspace_id: int, user: User) -> Workspace:
        return await self.require_role(workspace_id, user, WorkspaceMemberRole.VIEWER)

    async def update(self, workspace_id: int, user: User, payload: WorkspaceUpdate) -> Workspace:
        workspace = await self.require_role(workspace_id, user, WorkspaceMemberRole.OWNER)
        data = payload.model_dump(exclude_unset=True)
        return await self._workspaces.update(workspace, data)

    async def delete(self, workspace_id: int, user: User) -> None:
        workspace = await self.require_role(workspace_id, user, WorkspaceMemberRole.OWNER)
        await self._workspaces.delete(workspace)
