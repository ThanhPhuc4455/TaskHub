from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

PASSWORD = "password123"


async def login_as(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "User"},
    )
    response = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def user_id_of(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.get("/api/v1/users/me", headers=headers)
    return int(response.json()["id"])


async def create_workspace_and_project(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    workspace_name: str = "Workspace",
    project_name: str = "Project",
) -> tuple[int, int]:
    workspace = await client.post(
        "/api/v1/workspaces", json={"name": workspace_name}, headers=headers
    )
    assert workspace.status_code == 201
    workspace_id = int(workspace.json()["id"])
    project = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        json={"name": project_name},
        headers=headers,
    )
    assert project.status_code == 201
    return workspace_id, int(project.json()["id"])


@contextmanager
def capture_queries(engine: AsyncEngine) -> Iterator[list[str]]:
    statements: list[str] = []

    def capture_query(
        _: Any,
        __: Any,
        statement: str,
        ___: Any,
        ____: Any,
        _____: Any,
    ) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture_query)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_query)
