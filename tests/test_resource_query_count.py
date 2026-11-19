from typing import Any

from httpx import AsyncClient
from sqlalchemy import event

from app.main import app as fastapi_app
from tests.helpers import login_as
from tests.test_task_management import project_for


async def test_get_task_loads_workspace_membership_once(client: AsyncClient) -> None:
    owner = await login_as(client, "query-count-owner@example.com")
    project_id = await project_for(client, owner, "Query count workspace")
    created = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Query count task"},
        headers=owner,
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

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
        response = await client.get(f"/api/v1/tasks/{task_id}", headers=owner)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_query)

    assert response.status_code == 200
    membership_queries = [
        statement for statement in statements if "workspace_members" in statement.lower()
    ]
    assert len(statements) == 6
    assert len(membership_queries) == 1
