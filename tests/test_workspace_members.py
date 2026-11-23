from httpx import AsyncClient, Response

from tests.helpers import login_as, user_id_of

WS = "/api/v1/workspaces"


async def create_workspace(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.post(WS, json={"name": "Team A"}, headers=headers)
    assert response.status_code == 201
    return int(response.json()["id"])


async def invite(
    client: AsyncClient,
    workspace_id: int,
    headers: dict[str, str],
    email: str,
    role: str = "VIEWER",
) -> Response:
    return await client.post(
        f"{WS}/{workspace_id}/members", json={"email": email, "role": role}, headers=headers
    )


async def test_creator_is_owner_member(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    workspace_id = await create_workspace(client, owner)
    members = (await client.get(f"{WS}/{workspace_id}/members", headers=owner)).json()
    assert len(members) == 1
    assert members[0]["role"] == "OWNER"
    assert members[0]["user_id"] == await user_id_of(client, owner)


async def test_viewer_can_read_but_not_modify(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    viewer = await login_as(client, "viewer@example.com")
    workspace_id = await create_workspace(client, owner)
    assert (await invite(client, workspace_id, owner, "viewer@example.com")).status_code == 201

    assert (await client.get(f"{WS}/{workspace_id}", headers=viewer)).status_code == 200
    patch = await client.patch(f"{WS}/{workspace_id}", json={"name": "X"}, headers=viewer)
    assert patch.status_code == 403
    assert (await client.delete(f"{WS}/{workspace_id}", headers=viewer)).status_code == 403


async def test_editor_cannot_modify_workspace(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    editor = await login_as(client, "editor@example.com")
    workspace_id = await create_workspace(client, owner)
    await invite(client, workspace_id, owner, "editor@example.com", role="EDITOR")

    patch = await client.patch(f"{WS}/{workspace_id}", json={"name": "X"}, headers=editor)
    assert patch.status_code == 403


async def test_only_owner_can_invite(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    viewer = await login_as(client, "viewer@example.com")
    await login_as(client, "third@example.com")
    workspace_id = await create_workspace(client, owner)
    await invite(client, workspace_id, owner, "viewer@example.com")

    response = await invite(client, workspace_id, viewer, "third@example.com")
    assert response.status_code == 403


async def test_invite_validation(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    await login_as(client, "viewer@example.com")
    workspace_id = await create_workspace(client, owner)

    assert (await invite(client, workspace_id, owner, "viewer@example.com")).status_code == 201
    assert (await invite(client, workspace_id, owner, "viewer@example.com")).status_code == 409
    assert (await invite(client, workspace_id, owner, "nobody@example.com")).status_code == 404
    as_owner = await invite(client, workspace_id, owner, "viewer@example.com", role="OWNER")
    assert as_owner.status_code == 422


async def test_remove_member(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    viewer = await login_as(client, "viewer@example.com")
    workspace_id = await create_workspace(client, owner)
    await invite(client, workspace_id, owner, "viewer@example.com")

    viewer_id = await user_id_of(client, viewer)
    removed = await client.delete(f"{WS}/{workspace_id}/members/{viewer_id}", headers=owner)
    assert removed.status_code == 204
    assert (await client.get(f"{WS}/{workspace_id}", headers=viewer)).status_code == 404


async def test_cannot_remove_owner(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    workspace_id = await create_workspace(client, owner)
    owner_id = await user_id_of(client, owner)
    response = await client.delete(f"{WS}/{workspace_id}/members/{owner_id}", headers=owner)
    assert response.status_code == 400
