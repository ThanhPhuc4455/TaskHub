from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.workspace_member import WorkspaceMemberRole
from app.schemas.base import BaseSchema


class InviteMemberRequest(BaseSchema):
    email: EmailStr
    role: WorkspaceMemberRole = WorkspaceMemberRole.VIEWER

    @field_validator("role")
    @classmethod
    def cannot_invite_owner(cls, value: WorkspaceMemberRole) -> WorkspaceMemberRole:
        if value == WorkspaceMemberRole.OWNER:
            raise ValueError("cannot invite a member as OWNER")
        return value


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: int
    user_id: int
    role: WorkspaceMemberRole
