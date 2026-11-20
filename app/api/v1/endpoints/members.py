from fastapi import APIRouter, status

from app.api.deps import MemberServiceDep, WorkspaceOwner, WorkspaceViewer
from app.models.workspace_member import WorkspaceMember
from app.schemas.member import InviteMemberRequest, MemberRead

router = APIRouter(prefix="/workspaces/{workspace_id}/members", tags=["members"])


@router.get("", response_model=list[MemberRead])
async def list_members(
    workspace_id: int, service: MemberServiceDep, workspace: WorkspaceViewer
) -> list[WorkspaceMember]:
    return await service.list_members(workspace_id)


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
    workspace_id: int,
    user_id: int,
    service: MemberServiceDep,
    workspace: WorkspaceOwner,
) -> None:
    await service.remove(workspace, user_id)
