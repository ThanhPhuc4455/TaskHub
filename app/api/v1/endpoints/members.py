from typing import cast

from fastapi import APIRouter, status

from app.api.deps import (
    MemberServiceDep,
    PaginationDep,
    WorkspaceOwner,
    WorkspaceViewer,
)
from app.api.responses import RBAC_RESPONSES
from app.models.workspace_member import WorkspaceMember
from app.schemas.member import InviteMemberRequest, MemberRead, UpdateMemberRoleRequest
from app.schemas.page import PageResponse

router = APIRouter(
    prefix="/workspaces/{workspace_id}/members",
    tags=["members"],
    responses=RBAC_RESPONSES,
)


@router.get("", response_model=PageResponse[MemberRead])
async def list_members(
    workspace_id: int,
    service: MemberServiceDep,
    workspace: WorkspaceViewer,
    pagination: PaginationDep,
) -> PageResponse[MemberRead]:
    result = await service.list_members(workspace_id, pagination)
    return PageResponse.from_result(
        cast(list[MemberRead], result.items),
        result.total,
        pagination.page,
        pagination.limit,
    )


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: int,
    payload: InviteMemberRequest,
    service: MemberServiceDep,
    workspace: WorkspaceOwner,
) -> WorkspaceMember:
    return await service.invite(workspace_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: int,
    service: MemberServiceDep,
    workspace: WorkspaceOwner,
) -> None:
    await service.remove(workspace, user_id)


@router.patch("/{user_id}", response_model=MemberRead)
async def update_member_role(
    user_id: int,
    payload: UpdateMemberRoleRequest,
    service: MemberServiceDep,
    workspace: WorkspaceOwner,
) -> WorkspaceMember:
    return await service.update_role(workspace, user_id, payload)
