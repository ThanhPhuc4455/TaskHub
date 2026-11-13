from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageResult, Pagination
from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def list_by_workspace(
        self, workspace_id: int, pagination: Pagination
    ) -> PageResult[Project]:
        total = await self.session.scalar(
            select(func.count()).select_from(Project).where(Project.workspace_id == workspace_id)
        )
        stmt = (
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.scalars(stmt)
        return PageResult(items=list(result.all()), total=total or 0)
