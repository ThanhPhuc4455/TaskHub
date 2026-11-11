from datetime import UTC, datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        result = await self.session.scalars(select(RefreshToken).where(RefreshToken.jti == jti))
        return result.first()

    async def claim_for_rotation(self, jti: str, *, commit: bool = True) -> bool:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti, RefreshToken.revoked.is_(False))
            .values(revoked=True)
            .returning(RefreshToken.jti)
        )
        result = await self.session.execute(stmt)
        claimed = result.scalar_one_or_none() is not None
        await self._flush_or_commit(commit)
        return claimed

    async def revoke_all_for_user(self, user_id: int, *, commit: bool = True) -> int:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        result = await self.session.execute(stmt)
        await self._flush_or_commit(commit)
        return int(getattr(result, "rowcount", 0) or 0)

    async def delete_expired_or_revoked(self) -> int:
        stmt = delete(RefreshToken).where(
            or_(
                RefreshToken.revoked.is_(True),
                RefreshToken.expires_at <= datetime.now(UTC),
            )
        )
        result = await self.session.execute(stmt)
        await self.commit()
        return int(getattr(result, "rowcount", 0) or 0)
