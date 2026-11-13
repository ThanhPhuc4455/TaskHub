from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageResult, Pagination
from app.models.project import Project
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workspace)

    async def get_for_user(self, user_id: int, pagination: Pagination) -> PageResult[Workspace]:
        total = await self.session.scalar(
            select(func.count())
            .select_from(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.id)
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self.session.scalars(stmt)
        return PageResult(items=list(result.all()), total=total or 0)

    async def list_project_ids(self, workspace_id: int) -> list[int]:
        result = await self.session.scalars(
            select(Project.id).where(Project.workspace_id == workspace_id)
        )
        return list(result.all())
