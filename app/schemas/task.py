from datetime import UTC, datetime

from pydantic import ConfigDict, Field, PositiveInt, field_validator

from app.core.constants import TASK_TITLE_MAX_LENGTH, TASK_TITLE_MIN_LENGTH
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import BasePatchSchema, BaseSchema, PageResponse
from app.schemas.label import LabelRead
from app.schemas.user import UserSummary


class TaskCreate(BaseSchema):
    title: str = Field(min_length=TASK_TITLE_MIN_LENGTH, max_length=TASK_TITLE_MAX_LENGTH)
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: PositiveInt | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_in_future(cls, value: datetime | None) -> datetime | None:
        if value is not None and value <= datetime.now(UTC):
            raise ValueError("due_date must be in the future")
        return value


class TaskUpdate(BasePatchSchema):
    nullable_fields = frozenset({"description", "assignee_id", "due_date"})

    title: str | None = Field(
        default=None, min_length=TASK_TITLE_MIN_LENGTH, max_length=TASK_TITLE_MAX_LENGTH
    )
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: PositiveInt | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_in_future(cls, value: datetime | None) -> datetime | None:
        if value is not None and value <= datetime.now(UTC):
            raise ValueError("due_date must be in the future")
        return value


class TaskRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    assignee_id: int | None
    assignee: UserSummary | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_by: int
    created_at: datetime
    updated_at: datetime
    labels: list[LabelRead]


class TaskPageResponse(PageResponse[TaskRead]):
    pass
