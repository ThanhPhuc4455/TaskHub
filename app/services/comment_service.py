from dataclasses import dataclass

from app.core.cache import CacheBackend, invalidate_task_cache
from app.core.pagination import PageResult, Pagination
from app.models.comment import Comment
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate
from app.services.project_policy import ensure_comment_deletion_allowed, ensure_project_active
from app.services.task_service import TaskAccessContext


@dataclass(frozen=True)
class CommentAccessContext:
    comment: Comment
    task: TaskAccessContext


class CommentService:
    def __init__(self, comments: CommentRepository, cache: CacheBackend | None = None) -> None:
        self._comments = comments
        self._cache = cache

    async def _invalidate(self, project_id: int) -> None:
        if self._cache is not None:
            await invalidate_task_cache(self._cache, project_id)

    async def create(self, task: TaskAccessContext, user: User, payload: CommentCreate) -> Comment:
        ensure_project_active(task.project)
        comment = await self._comments.create(
            task_id=task.task.id,
            author_id=user.id,
            content=payload.content,
        )
        await self._invalidate(task.project.id)
        return (await self._comments.get_with_author(comment.id)) or comment

    async def list_comments(
        self, task: TaskAccessContext, pagination: Pagination
    ) -> PageResult[Comment]:
        return await self._comments.list_by_task(task.task.id, pagination)

    async def delete(self, access: CommentAccessContext, user: User) -> None:
        ensure_project_active(access.task.project)
        ensure_comment_deletion_allowed(
            access.comment.author_id, user.id, access.task.effective_role
        )
        await self._comments.delete(access.comment)
        await self._invalidate(access.task.project.id)
