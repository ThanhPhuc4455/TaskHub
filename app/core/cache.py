import hashlib
import json
import logging
from collections.abc import Sequence
from typing import Protocol, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.constants import TASK_CACHE_KEY_PREFIX, TASK_CACHE_TTL_SECONDS
from app.core.pagination import Pagination
from app.repositories.task_repository import TaskFilters

logger = logging.getLogger(__name__)
CACHE_BACKEND_ERRORS = (RedisError, OSError)


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, *, ttl: int) -> None: ...

    async def incr(self, key: str) -> int: ...


class RedisCacheBackend:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        return cast(str | None, await self._client.get(key))

    async def set(self, key: str, value: str, *, ttl: int) -> None:
        await self._client.set(key, value, ex=ttl)

    async def incr(self, key: str) -> int:
        return int(await self._client.incr(key))

    async def close(self) -> None:
        await self._client.aclose()


def create_redis_client() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )


def task_cache_version_key(project_id: int) -> str:
    return f"{TASK_CACHE_KEY_PREFIX}:{project_id}:tasks:ver"


def task_cache_data_key(
    project_id: int,
    version: int,
    filters: TaskFilters,
    pagination: Pagination,
) -> str:
    normalized = {
        "status": sorted(item.value for item in (filters.status or [])),
        "priority": sorted(item.value for item in (filters.priority or [])),
        "assignee_id": filters.assignee_id,
        "page": pagination.page,
        "limit": pagination.limit,
    }
    digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"{TASK_CACHE_KEY_PREFIX}:{project_id}:tasks:v{version}:{digest}"


async def read_task_cache(
    cache: CacheBackend,
    project_id: int,
    filters: TaskFilters,
    pagination: Pagination,
) -> tuple[str, str | None]:
    version_value = await cache.get(task_cache_version_key(project_id))
    version = int(version_value or 0)
    key = task_cache_data_key(project_id, version, filters, pagination)
    return key, await cache.get(key)


async def write_task_cache(cache: CacheBackend, key: str, value: str) -> None:
    await cache.set(key, value, ttl=settings.cache_ttl_seconds or TASK_CACHE_TTL_SECONDS)


async def invalidate_task_cache(cache: CacheBackend, project_id: int) -> None:
    try:
        await cache.incr(task_cache_version_key(project_id))
    except CACHE_BACKEND_ERRORS:
        logger.warning(
            "Task cache invalidation failed for project_id=%s", project_id, exc_info=True
        )


def task_cache_payload_json(items: Sequence[object], total: int, page: int, limit: int) -> str:
    from app.schemas.task import TaskPageResponse

    payload = TaskPageResponse(items=list(items), total=total, page=page, limit=limit)
    return payload.model_dump_json()
