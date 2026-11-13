import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import AuthenticationError
from app.core.security import create_refresh_token, hash_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


REVIEW8_DATABASE_URL = os.getenv("REVIEW8_DATABASE_URL")


@pytest_asyncio.fixture
async def postgres_sessionmaker() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    if not REVIEW8_DATABASE_URL:
        pytest.skip("REVIEW8_DATABASE_URL is required for PostgreSQL integration tests")
    engine = create_async_engine(REVIEW8_DATABASE_URL, pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def create_user_and_refresh_token(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    is_active: bool = True,
) -> tuple[int, str]:
    async with sessionmaker() as session:
        user = User(
            email=f"refresh-{uuid4().hex}@example.com",
            full_name="Refresh User",
            hashed_password=await hash_password("password123"),
            is_active=is_active,
        )
        session.add(user)
        await session.flush()
        issued = create_refresh_token(user.id)
        session.add(
            RefreshToken(
                jti=issued.jti,
                user_id=user.id,
                expires_at=issued.expires_at,
            )
        )
        await session.commit()
        return user.id, issued.token


async def refresh_in_new_session(
    sessionmaker: async_sessionmaker[AsyncSession], token: str
) -> bool:
    async with sessionmaker() as session:
        try:
            await AuthService(UserRepository(session), RefreshTokenRepository(session)).refresh(
                token
            )
        except AuthenticationError:
            return False
        return True


@pytest.mark.asyncio
async def test_concurrent_refresh_has_one_winner(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    _, token = await create_user_and_refresh_token(postgres_sessionmaker)
    results = await asyncio.gather(
        refresh_in_new_session(postgres_sessionmaker, token),
        refresh_in_new_session(postgres_sessionmaker, token),
    )
    assert sorted(results) == [False, True]
