from app.core.constants import FORBIDDEN_MESSAGE
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMemberRole
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    def __init__(self, workspaces: WorkspaceRepository, members: WorkspaceMemberRepository) -> None:
        self._workspaces = workspaces
        self._members = members

    async def require_role(
        self, workspace_id: int, user: User, required: WorkspaceMemberRole
    ) -> Workspace:
        workspace = await self._workspaces.get(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", workspace_id)
        if user.role == UserRole.ADMIN:
            return workspace
        membership = await self._members.get_membership(workspace_id, user.id)
        if membership is None:
            raise NotFoundError("Workspace", workspace_id)
        if membership.role.rank < required.rank:
            raise ForbiddenError(FORBIDDEN_MESSAGE)
        return workspace

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

    async def list_for_user(self, user: User) -> list[Workspace]:
        if user.role == UserRole.ADMIN:
            return await self._workspaces.get_all()
        return await self._workspaces.get_for_user(user.id)

    async def get(self, workspace_id: int, user: User) -> Workspace:
        return await self.require_role(workspace_id, user, WorkspaceMemberRole.VIEWER)

    async def update(self, workspace_id: int, user: User, payload: WorkspaceUpdate) -> Workspace:
        workspace = await self.require_role(workspace_id, user, WorkspaceMemberRole.OWNER)
        data = payload.model_dump(exclude_unset=True)
        return await self._workspaces.update(workspace, data)

    async def delete(self, workspace_id: int, user: User) -> None:
        workspace = await self.require_role(workspace_id, user, WorkspaceMemberRole.OWNER)
        await self._workspaces.delete(workspace)
