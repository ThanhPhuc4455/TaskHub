from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkspaceMember)

    async def get_membership(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        return await self.session.get(WorkspaceMember, (workspace_id, user_id))

    async def list_by_workspace(
        self, workspace_id: int, *, offset: int = 0, limit: int = 100
    ) -> list[WorkspaceMember]:
        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.user_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())
