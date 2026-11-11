from datetime import datetime

from pydantic import ConfigDict, Field

from app.core.constants import COMMENT_CONTENT_MAX_LENGTH, COMMENT_CONTENT_MIN_LENGTH
from app.schemas.base import BaseSchema
from app.schemas.user import UserSummary


class CommentCreate(BaseSchema):
    content: str = Field(
        min_length=COMMENT_CONTENT_MIN_LENGTH, max_length=COMMENT_CONTENT_MAX_LENGTH
    )


class CommentRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    author: UserSummary | None
    content: str
    created_at: datetime


class CommentPageResponse(BaseSchema):
    items: list[CommentRead]
    total: int
    page: int
    limit: int
