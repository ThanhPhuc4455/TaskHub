from dataclasses import dataclass

from app.core.constants import COMMENT_NOT_OWNER_MESSAGE, PROJECT_ARCHIVED_MESSAGE
from app.core.exceptions import BadRequestError, ForbiddenError
from app.core.pagination import Pagination
from app.models.comment import Comment
from app.models.enums import ProjectStatus, WorkspaceMemberRole
from app.models.project import Project
from app.models.user import User, UserRole
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate
from app.services.task_service import TaskAccessContext


@dataclass(frozen=True)
class CommentAccessContext:
    comment: Comment
    task: TaskAccessContext


class CommentService:
    def __init__(self, comments: CommentRepository) -> None:
        self._comments = comments

    @staticmethod
    def _ensure_active(project: Project) -> None:
        if project.status == ProjectStatus.ARCHIVED:
            raise BadRequestError(PROJECT_ARCHIVED_MESSAGE)

    async def create(self, task: TaskAccessContext, user: User, payload: CommentCreate) -> Comment:
        self._ensure_active(task.project)
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
        self._ensure_active(access.task.project)
        is_owner = access.task.workspace.effective_role.rank >= WorkspaceMemberRole.OWNER.rank
        if access.comment.author_id != user.id and user.role != UserRole.ADMIN and not is_owner:
            raise ForbiddenError(COMMENT_NOT_OWNER_MESSAGE)
        await self._comments.delete(access.comment)
