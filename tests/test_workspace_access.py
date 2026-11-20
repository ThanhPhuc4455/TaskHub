from httpx import AsyncClient

from tests.helpers import login_as

WS = "/api/v1/workspaces"


async def test_owner_sees_own_workspace(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    created = await client.post(WS, json={"name": "Team A"}, headers=owner)
    assert created.status_code == 201
    listing = await client.get(WS, headers=owner)
    assert [workspace["name"] for workspace in listing.json()] == ["Team A"]


async def test_other_user_does_not_see_workspace(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    stranger = await login_as(client, "stranger@example.com")
    workspace_id = (await client.post(WS, json={"name": "Team A"}, headers=owner)).json()["id"]

    assert (await client.get(WS, headers=stranger)).json() == []
    assert (await client.get(f"{WS}/{workspace_id}", headers=stranger)).status_code == 404
    patch = await client.patch(f"{WS}/{workspace_id}", json={"name": "X"}, headers=stranger)
    assert patch.status_code == 404
    assert (await client.delete(f"{WS}/{workspace_id}", headers=stranger)).status_code == 404
