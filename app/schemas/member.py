from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.messages import CANNOT_CHANGE_OWNER_ROLE_MESSAGE
from app.models.workspace_member import WorkspaceMemberRole
from app.schemas.base import BaseSchema, PageResponse


class InviteMemberRequest(BaseSchema):
    email: EmailStr
    role: WorkspaceMemberRole = WorkspaceMemberRole.VIEWER

    @field_validator("role")
    @classmethod
    def cannot_invite_owner(cls, value: WorkspaceMemberRole) -> WorkspaceMemberRole:
        if value == WorkspaceMemberRole.OWNER:
            raise ValueError(CANNOT_CHANGE_OWNER_ROLE_MESSAGE)
        return value


class UpdateMemberRoleRequest(BaseSchema):
    role: WorkspaceMemberRole

    @field_validator("role")
    @classmethod
    def cannot_assign_owner(cls, value: WorkspaceMemberRole) -> WorkspaceMemberRole:
        if value == WorkspaceMemberRole.OWNER:
            raise ValueError(CANNOT_CHANGE_OWNER_ROLE_MESSAGE)
        return value


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: int
    user_id: int
    role: WorkspaceMemberRole


class MemberPageResponse(PageResponse[MemberRead]):
    pass
