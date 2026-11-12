from dataclasses import dataclass

from app.core.pagination import Pagination
from app.models.comment import Comment
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate
from app.services.policies import ensure_comment_deletion_allowed, ensure_project_active
from app.services.task_service import TaskAccessContext


@dataclass(frozen=True)
class CommentAccessContext:
    comment: Comment
    task: TaskAccessContext


class CommentService:
    def __init__(self, comments: CommentRepository) -> None:
        self._comments = comments

    async def create(self, task: TaskAccessContext, user: User, payload: CommentCreate) -> Comment:
        ensure_project_active(task.project)
        comment = await self._comments.create(
            task_id=task.task.id,
            author_id=user.id,
            content=payload.content,
        )
        return (await self._comments.get_with_author(comment.id)) or comment

    async def list_comments(
        self, task: TaskAccessContext, pagination: Pagination
    ) -> tuple[list[Comment], int]:
        return await self._comments.list_by_task(
            task.task.id, offset=pagination.offset, limit=pagination.limit
        )

    async def delete(self, access: CommentAccessContext, user: User) -> None:
        ensure_project_active(access.task.project)
        ensure_comment_deletion_allowed(access.task, user, access.comment.author_id)
        await self._comments.delete(access.comment)
