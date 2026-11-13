from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient

from app.main import app as fastapi_app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository


async def test_delete_expired_keeps_live_and_revoked_live_tokens(
    auth_client: AsyncClient,
) -> None:
    sessionmaker = fastapi_app.state.test_sessionmaker
    async with sessionmaker() as session:
        user = User(
            email=f"cleanup-{uuid4().hex}@example.com",
            full_name="Cleanup User",
            hashed_password="unused",
        )
        session.add(user)
        await session.flush()
        now = datetime.now(UTC)
        expired = RefreshToken(
            jti=uuid4().hex,
            user_id=user.id,
            expires_at=now - timedelta(minutes=1),
            revoked=False,
        )
        live = RefreshToken(
            jti=uuid4().hex,
            user_id=user.id,
            expires_at=now + timedelta(minutes=1),
            revoked=False,
        )
        revoked_live = RefreshToken(
            jti=uuid4().hex,
            user_id=user.id,
            expires_at=now + timedelta(minutes=1),
            revoked=True,
        )
        session.add_all([expired, live, revoked_live])
        await session.commit()

        deleted = await RefreshTokenRepository(session).delete_expired()
        assert deleted == 1

        remaining = await RefreshTokenRepository(session).get_by_jti(live.jti)
        remaining_revoked = await RefreshTokenRepository(session).get_by_jti(revoked_live.jti)
        removed = await RefreshTokenRepository(session).get_by_jti(expired.jti)
        assert remaining is not None
        assert remaining_revoked is not None
        assert removed is None
