from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.pagination import PageResult, Pagination
from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def get_with_workspace(self, project_id: int) -> Project | None:
        return await self.session.scalar(
            select(Project).where(Project.id == project_id).options(joinedload(Project.workspace))
        )

    async def list_by_workspace(
        self, workspace_id: int, pagination: Pagination
    ) -> PageResult[Project]:
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
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.scalars(stmt)
        return PageResult(items=list(result.all()), total=total)
