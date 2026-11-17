from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MAX_PAGE_SIZE
from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def list_by_workspace(
        self, workspace_id: int, *, offset: int = 0, limit: int = MAX_PAGE_SIZE
    ) -> tuple[list[Project], int]:
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Project)
                .where(Project.workspace_id == workspace_id)
            )
            or 0
        )
        stmt = (
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all()), total
