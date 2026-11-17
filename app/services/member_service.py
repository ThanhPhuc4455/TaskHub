from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.messages import (
    ALREADY_MEMBER_MESSAGE,
    CANNOT_CHANGE_OWNER_ROLE_MESSAGE,
    CANNOT_REMOVE_OWNER_MESSAGE,
)
from app.core.pagination import Pagination
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
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

    async def list_members(
        self, workspace_id: int, pagination: Pagination
    ) -> tuple[list[WorkspaceMember], int]:
        return await self._members.list_by_workspace(
            workspace_id, offset=pagination.offset, limit=pagination.limit
        )

    async def invite(self, workspace_id: int, payload: InviteMemberRequest) -> WorkspaceMember:
        invitee = await self._users.get_by_email(payload.email.lower())
        if invitee is None:
            raise NotFoundError("User", payload.email)
        if await self._members.get_membership(workspace_id, invitee.id) is not None:
            raise ConflictError(ALREADY_MEMBER_MESSAGE)
        try:
            return await self._members.create(
                workspace_id=workspace_id, user_id=invitee.id, role=payload.role
            )
        except IntegrityError as exc:
            await self._members.rollback()
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise ConflictError(ALREADY_MEMBER_MESSAGE) from exc
            raise

    async def remove(self, workspace: Workspace, target_user_id: int) -> None:
        if target_user_id == workspace.owner_id:
            raise BadRequestError(CANNOT_REMOVE_OWNER_MESSAGE)
        membership = await self._members.get_membership(workspace.id, target_user_id)
        if membership is None:
            raise NotFoundError("Member", target_user_id)
        await self._members.delete(membership)

    async def update_role(
        self,
        workspace: Workspace,
        target_user_id: int,
        payload: UpdateMemberRoleRequest,
    ) -> WorkspaceMember:
        if target_user_id == workspace.owner_id:
            raise BadRequestError(CANNOT_CHANGE_OWNER_ROLE_MESSAGE)
        membership = await self._members.get_membership(workspace.id, target_user_id)
        if membership is None:
            raise NotFoundError("Member", target_user_id)
        return await self._members.update(membership, {"role": payload.role})
