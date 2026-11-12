from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Label)

    async def list_by_project(self, project_id: int, *, offset: int, limit: int) -> list[Label]:
        result = await self.session.scalars(
            select(Label)
            .where(Label.project_id == project_id)
            .order_by(Label.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())
