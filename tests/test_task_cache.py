from collections.abc import AsyncIterator

import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from httpx import AsyncClient

from app.api.deps import get_cache_backend
from app.core.cache import task_cache_data_key, task_cache_version_key
from app.core.pagination import Pagination
from app.main import app as fastapi_app
from app.models.enums import TaskPriority, TaskStatus
from app.repositories.task_repository import TaskFilters, TaskPage, TaskRepository
from tests.helpers import login_as


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.increments: list[str] = []
        self.fail = False

    async def get(self, key: str) -> str | None:
        if self.fail:
            raise ConnectionError("cache unavailable")
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ttl: int) -> None:
        if self.fail:
            raise ConnectionError("cache unavailable")
        self.values[key] = value
        self.ttls[key] = ttl

    async def incr(self, key: str) -> int:
        if self.fail:
            raise ConnectionError("cache unavailable")
        self.increments.append(key)
        value = int(self.values.get(key, "0")) + 1
        self.values[key] = str(value)
        return value


@pytest_asyncio.fixture
async def fake_cache(client: AsyncClient) -> AsyncIterator[FakeCache]:
    cache = FakeCache()

    async def override_cache() -> AsyncIterator[FakeCache]:
        yield cache

    fastapi_app.dependency_overrides[get_cache_backend] = override_cache
    yield cache
    fastapi_app.dependency_overrides.pop(get_cache_backend, None)


async def create_project(client: AsyncClient, headers: dict[str, str]) -> int:
    workspace = await client.post(
        "/api/v1/workspaces", json={"name": "Cache workspace"}, headers=headers
    )
    assert workspace.status_code == 201
    project = await client.post(
        f"/api/v1/workspaces/{workspace.json()['id']}/projects",
        json={"name": "Cache project"},
        headers=headers,
    )
    assert project.status_code == 201
    return int(project.json()["id"])


def test_task_cache_key_normalizes_filter_order() -> None:
    pagination = Pagination(page=1, limit=20)
    first = TaskFilters(
        status=[TaskStatus.DONE, TaskStatus.TODO],
        priority=[TaskPriority.HIGH, TaskPriority.LOW],
        assignee_id=4,
    )
    second = TaskFilters(
        status=[TaskStatus.TODO, TaskStatus.DONE],
        priority=[TaskPriority.LOW, TaskPriority.HIGH],
        assignee_id=4,
    )
    assert task_cache_data_key(7, 2, first, pagination) == task_cache_data_key(
        7, 2, second, pagination
    )
    assert task_cache_data_key(7, 2, first, pagination) != task_cache_data_key(
        8, 2, first, pagination
    )


async def test_task_cache_hit_avoids_second_repository_query(
    client: AsyncClient, fake_cache: FakeCache, monkeypatch: MonkeyPatch
) -> None:
    headers = await login_as(client, "cache-owner@example.com")
    project_id = await create_project(client, headers)
    created = await client.post(
        f"/api/v1/projects/{project_id}/tasks", json={"title": "Cached task"}, headers=headers
    )
    assert created.status_code == 201

    calls = 0
    original = TaskRepository.list_by_project

    async def counted(
        self: TaskRepository, project: int, filters: TaskFilters, pagination: Pagination
    ) -> TaskPage:
        nonlocal calls
        calls += 1
        return await original(self, project, filters, pagination)

    monkeypatch.setattr(TaskRepository, "list_by_project", counted)
    first = await client.get(f"/api/v1/projects/{project_id}/tasks", headers=headers)
    second = await client.get(f"/api/v1/projects/{project_id}/tasks", headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls == 1
    assert fake_cache.ttls
    assert set(fake_cache.ttls.values()) == {120}


async def test_task_cache_failure_falls_back_to_database(
    client: AsyncClient, fake_cache: FakeCache
) -> None:
    headers = await login_as(client, "cache-failure@example.com")
    project_id = await create_project(client, headers)
    await client.post(
        f"/api/v1/projects/{project_id}/tasks", json={"title": "Database task"}, headers=headers
    )
    fake_cache.fail = True

    response = await client.get(f"/api/v1/projects/{project_id}/tasks", headers=headers)

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "Database task"


async def test_task_mutation_increments_project_cache_version(
    client: AsyncClient, fake_cache: FakeCache
) -> None:
    headers = await login_as(client, "cache-invalidation@example.com")
    project_id = await create_project(client, headers)
    created = await client.post(
        f"/api/v1/projects/{project_id}/tasks", json={"title": "Mutable task"}, headers=headers
    )
    task_id = created.json()["id"]
    version_key = task_cache_version_key(project_id)
    assert version_key in fake_cache.increments

    await client.patch(f"/api/v1/tasks/{task_id}", json={"status": "DONE"}, headers=headers)
    await client.delete(f"/api/v1/tasks/{task_id}", headers=headers)

    assert fake_cache.increments.count(version_key) == 3
