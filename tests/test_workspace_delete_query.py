from typing import Any

from httpx import AsyncClient
from sqlalchemy import event

from app.main import app as fastapi_app


async def test_delete_workspace_checks_membership_once(client: AsyncClient) -> None:
    owner = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "workspace-delete-query@example.com",
            "full_name": "Workspace Delete Query",
            "password": "password123",
        },
    )
    assert owner.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "workspace-delete-query@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = await client.post(
        "/api/v1/workspaces", json={"name": "Delete query workspace"}, headers=headers
    )
    assert created.status_code == 201
    workspace_id = created.json()["id"]

    engine = fastapi_app.state.test_sessionmaker.kw["bind"]
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
        response = await client.delete(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_query)

    assert response.status_code == 204
    membership_queries = [
        statement for statement in statements if "workspace_members" in statement.lower()
    ]
    assert len(membership_queries) == 1
