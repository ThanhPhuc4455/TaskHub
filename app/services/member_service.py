from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.messages import ALREADY_MEMBER_MESSAGE, CANNOT_REMOVE_OWNER_MESSAGE
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.member import InviteMemberRequest
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

    async def list_members(self, workspace_id: int) -> list[WorkspaceMember]:
        return await self._members.list_by_workspace(workspace_id)

    async def invite(
        self, workspace_id: int, payload: InviteMemberRequest
    ) -> WorkspaceMember:
        invitee = await self._users.get_by_email(payload.email.lower())
        if invitee is None:
            raise NotFoundError("User", payload.email)
        if await self._members.get_membership(workspace_id, invitee.id) is not None:
            raise ConflictError(ALREADY_MEMBER_MESSAGE)
        return await self._members.create(
            workspace_id=workspace_id, user_id=invitee.id, role=payload.role
        )

    async def remove(self, workspace: Workspace, target_user_id: int) -> None:
        if target_user_id == workspace.owner_id:
            raise BadRequestError(CANNOT_REMOVE_OWNER_MESSAGE)
        membership = await self._members.get_membership(workspace.id, target_user_id)
        if membership is None:
            raise NotFoundError("Member", target_user_id)
        await self._members.delete(membership)
