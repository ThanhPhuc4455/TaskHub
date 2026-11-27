from httpx import AsyncClient

from app.main import app as fastapi_app
from tests.helpers import capture_queries


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
    with capture_queries(engine) as statements:
        response = await client.delete(f"/api/v1/workspaces/{workspace_id}", headers=headers)

    assert response.status_code == 204
    membership_queries = [
        statement for statement in statements if "workspace_members" in statement.lower()
    ]
    assert len(membership_queries) == 1
