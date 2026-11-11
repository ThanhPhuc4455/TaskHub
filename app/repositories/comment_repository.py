from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Comment)

    async def get_with_author(self, comment_id: int) -> Comment | None:
        return await self.session.scalar(
            select(Comment).where(Comment.id == comment_id).options(selectinload(Comment.author))
        )

    async def list_by_task(
        self, task_id: int, *, offset: int, limit: int
    ) -> tuple[list[Comment], int]:
        total = await self.session.scalar(
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )
        result = await self.session.scalars(
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.desc(), Comment.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all()), total or 0
