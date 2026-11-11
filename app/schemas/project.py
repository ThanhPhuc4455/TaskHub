from datetime import datetime

from pydantic import ConfigDict, Field

from app.core.constants import PROJECT_NAME_MAX_LENGTH, PROJECT_NAME_MIN_LENGTH
from app.models.enums import ProjectStatus
from app.schemas.base import BasePatchSchema, BaseSchema


class ProjectCreate(BaseSchema):
    name: str = Field(min_length=PROJECT_NAME_MIN_LENGTH, max_length=PROJECT_NAME_MAX_LENGTH)
    description: str | None = None


class ProjectUpdate(BasePatchSchema):
    nullable_fields = frozenset({"description"})

    name: str | None = Field(
        default=None,
        min_length=PROJECT_NAME_MIN_LENGTH,
        max_length=PROJECT_NAME_MAX_LENGTH,
    )
    description: str | None = None


class ProjectRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
