from fastapi import APIRouter, status

from app.api.deps import CurrentUser, MemberServiceDep, PaginationDep
from app.models.workspace_member import WorkspaceMember
from app.schemas.member import InviteMemberRequest, MemberRead, UpdateMemberRoleRequest

router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["members"])


@router.get("", response_model=list[MemberRead])
async def list_members(
    workspace_id: int,
    service: MemberServiceDep,
    current_user: CurrentUser,
    pagination: PaginationDep,
) -> list[WorkspaceMember]:
    return await service.list_members(workspace_id, current_user, pagination)


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: int,
    payload: InviteMemberRequest,
    service: MemberServiceDep,
    current_user: CurrentUser,
) -> WorkspaceMember:
    return await service.invite(workspace_id, current_user, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: int, user_id: int, service: MemberServiceDep, current_user: CurrentUser
) -> None:
    await service.remove(workspace_id, current_user, user_id)


@router.patch("/{user_id}", response_model=MemberRead)
async def update_member_role(
    workspace_id: int,
    user_id: int,
    payload: UpdateMemberRoleRequest,
    service: MemberServiceDep,
    current_user: CurrentUser,
) -> WorkspaceMember:
    return await service.update_role(workspace_id, current_user, user_id, payload)
