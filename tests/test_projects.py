from httpx import AsyncClient
from sqlalchemy import select

from app.main import app as fastapi_app
from app.models.user import User, UserRole
from tests.helpers import create_workspace_and_project, login_as

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


async def promote_to_admin(email: str) -> None:
    async with fastapi_app.state.test_sessionmaker() as session:
        user = await session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = UserRole.ADMIN
        await session.commit()


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
    _, project_id = await create_workspace_and_project(
        client, owner, workspace_name="Team A", project_name="Project"
    )

    archive = await client.post(f"/api/v1/projects/{project_id}/archive", headers=owner)
    assert archive.status_code == 200
    assert archive.json()["status"] == "ARCHIVED"

    archive_again = await client.post(f"/api/v1/projects/{project_id}/archive", headers=owner)
    assert archive_again.status_code == 409
    assert archive_again.json()["detail"] == "Archived projects cannot be modified"

    update = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "No longer editable"},
        headers=owner,
    )
    assert update.status_code == 409

    deleted = await client.delete(f"/api/v1/projects/{project_id}", headers=owner)
    assert deleted.status_code == 204


async def test_workspace_delete_cascades_projects(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    workspace_id, project_id = await create_workspace_and_project(
        client, owner, workspace_name="Team A", project_name="Project"
    )

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
        f"{WS}/{workspace_id}/projects?page=1&limit=1",
        headers=owner,
    )
    assert response.status_code == 200
    first_page = response.json()
    assert [project["name"] for project in first_page["items"]] == ["Project A"]
    assert first_page["total"] == 2

    response = await client.get(
        f"{WS}/{workspace_id}/projects?page=2&limit=1",
        headers=owner,
    )
    second_page = response.json()
    assert [project["name"] for project in second_page["items"]] == ["Project B"]
    assert second_page["total"] == 2


async def test_project_idor_is_hidden_from_other_workspace(client: AsyncClient) -> None:
    owner_a = await login_as(client, "owner-a@example.com")
    owner_b = await login_as(client, "owner-b@example.com")
    _, project_id = await create_workspace_and_project(
        client, owner_a, workspace_name="Team A", project_name="Private project"
    )

    assert (await client.get(f"/api/v1/projects/{project_id}", headers=owner_b)).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Stolen"},
            headers=owner_b,
        )
    ).status_code == 404


async def test_project_list_hides_workspace_from_outsider(client: AsyncClient) -> None:
    owner = await login_as(client, "list-owner@example.com")
    outsider = await login_as(client, "list-outsider@example.com")
    workspace_id = await create_workspace(client, owner)

    response = await client.get(f"{WS}/{workspace_id}/projects", headers=outsider)

    assert response.status_code == 404


async def test_admin_can_access_project_in_another_workspace(client: AsyncClient) -> None:
    owner = await login_as(client, "project-owner@example.com")
    _, project_id = await create_workspace_and_project(
        client, owner, workspace_name="Team A", project_name="Admin-visible project"
    )

    await login_as(client, "project-admin@example.com")
    await promote_to_admin("project-admin@example.com")
    admin = await login_as(client, "project-admin@example.com")

    response = await client.get(f"/api/v1/projects/{project_id}", headers=admin)
    assert response.status_code == 200
    assert response.json()["id"] == project_id
