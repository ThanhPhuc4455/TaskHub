from app.core.constants import (
    ALREADY_MEMBER_MESSAGE,
    CANNOT_CHANGE_OWNER_ROLE_MESSAGE,
    CANNOT_REMOVE_OWNER_MESSAGE,
)
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.user import User
from app.models.workspace_member import WorkspaceMember, WorkspaceMemberRole
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.member import InviteMemberRequest, UpdateMemberRoleRequest
from app.services.workspace_service import WorkspaceService


class MemberService:
    def __init__(
        self,
        workspaces: WorkspaceService,
        members: WorkspaceMemberRepository,
        users: UserRepository,
    ) -> None:
        self._workspaces = workspaces
        self._members = members
        self._users = users

    async def list_members(self, workspace_id: int, user: User) -> list[WorkspaceMember]:
        await self._workspaces.require_role(workspace_id, user, WorkspaceMemberRole.VIEWER)
        return await self._members.list_by_workspace(workspace_id)

    async def invite(
        self, workspace_id: int, user: User, payload: InviteMemberRequest
    ) -> WorkspaceMember:
        await self._workspaces.require_role(workspace_id, user, WorkspaceMemberRole.OWNER)
        invitee = await self._users.get_by_email(payload.email.lower())
        if invitee is None:
            raise NotFoundError("User", payload.email)
        if await self._members.get_membership(workspace_id, invitee.id) is not None:
            raise ConflictError(ALREADY_MEMBER_MESSAGE)
        return await self._members.create(
            workspace_id=workspace_id, user_id=invitee.id, role=payload.role
        )

    async def remove(self, workspace_id: int, user: User, target_user_id: int) -> None:
        workspace = await self._workspaces.require_role(
            workspace_id, user, WorkspaceMemberRole.OWNER
        )
        if target_user_id == workspace.owner_id:
            raise BadRequestError(CANNOT_CHANGE_OWNER_ROLE_MESSAGE)
        membership = await self._members.get_membership(workspace_id, target_user_id)
        if membership is None:
            raise NotFoundError("Member", target_user_id)
        await self._members.delete(membership)

    async def update_role(
        self,
        workspace_id: int,
        user: User,
        target_user_id: int,
        payload: UpdateMemberRoleRequest,
    ) -> WorkspaceMember:
        workspace = await self._workspaces.require_role(
            workspace_id, user, WorkspaceMemberRole.OWNER
        )
        if target_user_id == workspace.owner_id:
            raise BadRequestError(CANNOT_REMOVE_OWNER_MESSAGE)
        membership = await self._members.get_membership(workspace_id, target_user_id)
        if membership is None:
            raise NotFoundError("Member", target_user_id)
        return await self._members.update(membership, {"role": payload.role})
