from httpx import AsyncClient

from app.main import app as fastapi_app
from tests.helpers import capture_queries, create_workspace_and_project, login_as


async def test_get_task_loads_workspace_membership_once(client: AsyncClient) -> None:
    owner = await login_as(client, "query-count-owner@example.com")
    _, project_id = await create_workspace_and_project(
        client, owner, workspace_name="Query count workspace"
    )
    created = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Query count task"},
        headers=owner,
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    engine = fastapi_app.state.test_sessionmaker.kw["bind"]
    with capture_queries(engine) as statements:
        response = await client.get(f"/api/v1/tasks/{task_id}", headers=owner)

    assert response.status_code == 200
    membership_queries = [
        statement for statement in statements if "workspace_members" in statement.lower()
    ]
    assert len(statements) == 6
    assert len(membership_queries) == 1


async def test_get_project_query_count(client: AsyncClient) -> None:
    owner = await login_as(client, "project-query-owner@example.com")
    _, project_id = await create_workspace_and_project(
        client, owner, workspace_name="Project query count workspace"
    )

    engine = fastapi_app.state.test_sessionmaker.kw["bind"]
    with capture_queries(engine) as statements:
        response = await client.get(f"/api/v1/projects/{project_id}", headers=owner)

    assert response.status_code == 200
    assert len(statements) == 3


async def test_list_tasks_query_count(client: AsyncClient) -> None:
    owner = await login_as(client, "tasks-query-owner@example.com")
    _, project_id = await create_workspace_and_project(
        client, owner, workspace_name="Tasks query count workspace"
    )
    created = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Query count task"},
        headers=owner,
    )
    assert created.status_code == 201

    engine = fastapi_app.state.test_sessionmaker.kw["bind"]
    with capture_queries(engine) as statements:
        response = await client.get(f"/api/v1/projects/{project_id}/tasks", headers=owner)

    assert response.status_code == 200
    assert len(statements) == 7
