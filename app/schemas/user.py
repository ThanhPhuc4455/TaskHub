from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import FULL_NAME_MAX_LENGTH, FULL_NAME_MIN_LENGTH
from app.models.user import UserRole
from app.schemas.base import BasePatchSchema
from app.schemas.types import Password


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str


class UserUpdate(BasePatchSchema):
    full_name: str | None = Field(
        default=None, min_length=FULL_NAME_MIN_LENGTH, max_length=FULL_NAME_MAX_LENGTH
    )


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Password
