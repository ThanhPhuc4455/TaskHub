import os
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-0123456789")

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_cache_backend
from app.core.database import get_db_session
from app.main import app as fastapi_app
from app.models.base import Base


class NoopCache:
    async def get(self, key: str) -> None:
        return None

    async def set(self, key: str, value: str, *, ttl: int) -> None:
        return None

    async def incr(self, key: str) -> int:
        return 1


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with maker() as session:
            yield session

    async def override_cache() -> AsyncIterator[NoopCache]:
        yield NoopCache()

    fastapi_app.state.test_sessionmaker = maker
    fastapi_app.dependency_overrides[get_db_session] = override_get_db
    fastapi_app.dependency_overrides[get_cache_backend] = override_cache
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()
    del fastapi_app.state.test_sessionmaker
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    user = {"email": "owner@example.com", "password": "password123", "full_name": "Owner"}
    await client.post("/api/v1/auth/register", json=user)
    response = await client.post(
        "/api/v1/auth/login", data={"username": user["email"], "password": user["password"]}
    )
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client
