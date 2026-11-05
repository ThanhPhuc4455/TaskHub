from httpx import AsyncClient

BASE = "/api/v1/workspaces"


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_workspace_crud(client: AsyncClient) -> None:
    created = await client.post(BASE, json={"name": "Team A"})
    assert created.status_code == 201
    workspace_id = created.json()["id"]

    assert (await client.get(f"{BASE}/{workspace_id}")).status_code == 200

    updated = await client.patch(f"{BASE}/{workspace_id}", json={"name": "Team B"})
    assert updated.json()["name"] == "Team B"

    assert (await client.delete(f"{BASE}/{workspace_id}")).status_code == 204
    assert (await client.get(f"{BASE}/{workspace_id}")).status_code == 404


async def test_create_with_empty_name_returns_422(client: AsyncClient) -> None:
    assert (await client.post(BASE, json={"name": ""})).status_code == 422
