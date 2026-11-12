from httpx import AsyncClient

from tests.helpers import login_as

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
    role: str,
) -> None:
    response = await client.post(
        f"{WS}/{workspace_id}/members",
        json={"email": email, "role": role},
        headers=headers,
    )
    assert response.status_code == 201


async def test_project_endpoints_require_auth(client: AsyncClient) -> None:
    assert (await client.post(f"{WS}/1/projects", json={"name": "Project"})).status_code == 401


async def test_viewer_cannot_create_project(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    viewer = await login_as(client, "viewer@example.com")
    workspace_id = await create_workspace(client, owner)
    await invite(client, workspace_id, owner, "viewer@example.com", "VIEWER")

    response = await client.post(
        f"{WS}/{workspace_id}/projects",
        json={"name": "Project"},
        headers=viewer,
    )
    assert response.status_code == 403


async def test_editor_can_create_and_update_but_not_archive(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    editor = await login_as(client, "editor@example.com")
    workspace_id = await create_workspace(client, owner)
    await invite(client, workspace_id, owner, "editor@example.com", "EDITOR")

    created = await client.post(
        f"{WS}/{workspace_id}/projects",
        json={"name": "Project"},
        headers=editor,
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"description": "Updated"},
        headers=editor,
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"

    archive = await client.post(f"/api/v1/projects/{project_id}/archive", headers=editor)
    assert archive.status_code == 403


async def test_owner_can_archive_project(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    workspace_id = await create_workspace(client, owner)
    created = await client.post(
        f"{WS}/{workspace_id}/projects",
        json={"name": "Project"},
        headers=owner,
    )
    project_id = created.json()["id"]

    archive = await client.post(f"/api/v1/projects/{project_id}/archive", headers=owner)
    assert archive.status_code == 200
    assert archive.json()["status"] == "ARCHIVED"

    update = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "No longer editable"},
        headers=owner,
    )
    assert update.status_code == 400

    deleted = await client.delete(f"/api/v1/projects/{project_id}", headers=owner)
    assert deleted.status_code == 204


async def test_workspace_delete_cascades_projects(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    workspace_id = await create_workspace(client, owner)
    created = await client.post(
        f"{WS}/{workspace_id}/projects",
        json={"name": "Project"},
        headers=owner,
    )
    project_id = created.json()["id"]

    deleted = await client.delete(f"{WS}/{workspace_id}", headers=owner)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/projects/{project_id}", headers=owner)).status_code == 404


async def test_project_list_supports_pagination(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    workspace_id = await create_workspace(client, owner)
    for name in ("Project A", "Project B"):
        response = await client.post(
            f"{WS}/{workspace_id}/projects",
            json={"name": name},
            headers=owner,
        )
        assert response.status_code == 201

    response = await client.get(
        f"{WS}/{workspace_id}/projects?page=2&limit=1",
        headers=owner,
    )
    assert response.status_code == 200
    assert [project["name"] for project in response.json()] == ["Project B"]


async def test_project_idor_is_hidden_from_other_workspace(client: AsyncClient) -> None:
    owner_a = await login_as(client, "owner-a@example.com")
    owner_b = await login_as(client, "owner-b@example.com")
    workspace_a = await create_workspace(client, owner_a)
    created = await client.post(
        f"{WS}/{workspace_a}/projects",
        json={"name": "Private project"},
        headers=owner_a,
    )
    project_id = created.json()["id"]

    assert (await client.get(f"/api/v1/projects/{project_id}", headers=owner_b)).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Stolen"},
            headers=owner_b,
        )
    ).status_code == 404
