from httpx import AsyncClient

BASE = "/api/v1/workspaces"


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_workspace_crud(auth_client: AsyncClient) -> None:
    created = await auth_client.post(BASE, json={"name": "Team A"})
    assert created.status_code == 201
    workspace_id = created.json()["id"]

    assert (await auth_client.get(f"{BASE}/{workspace_id}")).status_code == 200

    updated = await auth_client.patch(f"{BASE}/{workspace_id}", json={"name": "Team B"})
    assert updated.json()["name"] == "Team B"

    assert (await auth_client.delete(f"{BASE}/{workspace_id}")).status_code == 204
    assert (await auth_client.get(f"{BASE}/{workspace_id}")).status_code == 404


async def test_create_with_empty_name_returns_422(auth_client: AsyncClient) -> None:
    assert (await auth_client.post(BASE, json={"name": ""})).status_code == 422


async def test_patch_null_name_returns_422(auth_client: AsyncClient) -> None:
    created = await auth_client.post(BASE, json={"name": "Team A"})
    workspace_id = created.json()["id"]
    response = await auth_client.patch(f"{BASE}/{workspace_id}", json={"name": None})
    assert response.status_code == 422
    assert (await auth_client.get(f"{BASE}/{workspace_id}")).status_code == 200


async def test_workspaces_require_login(client: AsyncClient) -> None:
    assert (await client.get(BASE)).status_code == 401


async def test_workspace_list_supports_pagination(auth_client: AsyncClient) -> None:
    await auth_client.post(BASE, json={"name": "Team A"})
    await auth_client.post(BASE, json={"name": "Team B"})

    response = await auth_client.get(f"{BASE}?page=2&limit=1")
    assert response.status_code == 200
    assert [workspace["name"] for workspace in response.json()] == ["Team B"]
