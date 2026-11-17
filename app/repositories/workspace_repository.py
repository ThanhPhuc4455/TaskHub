from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MAX_PAGE_SIZE
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workspace)

    async def get_for_user(
        self, user_id: int, *, offset: int = 0, limit: int = MAX_PAGE_SIZE
    ) -> tuple[list[Workspace], int]:
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Workspace)
                .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
                .where(WorkspaceMember.user_id == user_id)
            )
            or 0
        )
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all()), total
