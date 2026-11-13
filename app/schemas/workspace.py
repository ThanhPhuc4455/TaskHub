from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import WORKSPACE_NAME_MAX_LENGTH, WORKSPACE_NAME_MIN_LENGTH
from app.schemas.base import BasePatchSchema, BaseSchema, PageResponse


class WorkspaceCreate(BaseSchema):
    name: str = Field(
        min_length=WORKSPACE_NAME_MIN_LENGTH,
        max_length=WORKSPACE_NAME_MAX_LENGTH,
    )


class WorkspaceUpdate(BasePatchSchema):
    name: str | None = Field(
        default=None,
        min_length=WORKSPACE_NAME_MIN_LENGTH,
        max_length=WORKSPACE_NAME_MAX_LENGTH,
    )


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime


class WorkspacePageResponse(PageResponse[WorkspaceRead]):
    pass
