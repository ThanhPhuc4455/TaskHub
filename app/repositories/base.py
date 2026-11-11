from typing import Any

from sqlalchemy import func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


class BaseRepository[ModelT: Base]:
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def commit(self) -> None:
        await self.session.commit()

    async def _flush_or_commit(self, commit: bool) -> None:
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

    async def create(self, *, commit: bool = True, **data: Any) -> ModelT:
        obj = self.model(**data)
        self.session.add(obj)
        await self._flush_or_commit(commit)
        await self.session.refresh(obj)
        return obj

    async def get(self, obj_id: int) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def get_all(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        primary_key = inspect(self.model).primary_key[0]
        stmt = select(self.model).order_by(primary_key).offset(offset).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(self.model))
        return result or 0

    async def update(self, obj: ModelT, data: dict[str, Any], *, commit: bool = True) -> ModelT:
        for key, value in data.items():
            setattr(obj, key, value)
        await self._flush_or_commit(commit)
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT, *, commit: bool = True) -> None:
        await self.session.delete(obj)
        await self._flush_or_commit(commit)
