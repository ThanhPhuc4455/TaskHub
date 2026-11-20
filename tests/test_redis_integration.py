import json
import time
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.api.deps import get_cache_backend
from app.core.cache import RedisCacheBackend
from app.core.config import settings
from app.main import app as fastapi_app
from tests.helpers import login_as

pytestmark = pytest.mark.redis_integration


@pytest_asyncio.fixture
async def real_redis() -> AsyncIterator[tuple[Redis, RedisCacheBackend]]:
    client = Redis.from_url(
        settings.redis_url,
        db=1,
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )
    try:
        try:
            await client.ping()
        except (RedisError, OSError) as exc:
            pytest.skip(f"Redis integration unavailable: {exc}")
        yield client, RedisCacheBackend(client)
    finally:
        async for key in client.scan_iter(match="project:integration:*"):
            await client.delete(key)
        await client.aclose()


async def test_real_redis_set_get_json_and_ttl(
    real_redis: tuple[Redis, RedisCacheBackend],
) -> None:
    client, backend = real_redis
    key = f"project:integration:{uuid4().hex}:json"
    value = {"items": [{"id": 1, "title": "real redis"}], "total": 1}

    await backend.set(key, json.dumps(value), ttl=settings.cache_ttl_seconds)
    stored = await backend.get(key)
    ttl = await client.ttl(key)

    assert stored is not None
    assert json.loads(stored) == value
    assert 0 < ttl <= settings.cache_ttl_seconds


async def test_real_redis_incr_and_missing_key(
    real_redis: tuple[Redis, RedisCacheBackend],
) -> None:
    _, backend = real_redis
    key = f"project:integration:{uuid4().hex}:tasks:ver"

    assert await backend.get(f"{key}:missing") is None
    assert await backend.incr(key) == 1
    assert await backend.incr(key) == 2
    assert await backend.get(key) == "2"


async def test_wrong_port_falls_back_to_database_quickly(
    client: AsyncClient,
    real_redis: tuple[Redis, RedisCacheBackend],
) -> None:
    del real_redis
    headers = await login_as(client, "redis-fallback@example.com")
    workspace = await client.post(
        "/api/v1/workspaces", json={"name": "Redis fallback"}, headers=headers
    )
    project = await client.post(
        f"/api/v1/workspaces/{workspace.json()['id']}/projects",
        json={"name": "Fallback project"},
        headers=headers,
    )
    project_id = project.json()["id"]
    await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Fallback task"},
        headers=headers,
    )

    wrong_client = Redis.from_url(
        "redis://127.0.0.1:6390/1",
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )
    fastapi_app.dependency_overrides[get_cache_backend] = lambda: RedisCacheBackend(wrong_client)
    started = time.perf_counter()
    try:
        response = await client.get(f"/api/v1/projects/{project_id}/tasks", headers=headers)
    finally:
        fastapi_app.dependency_overrides.pop(get_cache_backend, None)
        await wrong_client.aclose()

    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Fallback task"
    assert elapsed < 3
