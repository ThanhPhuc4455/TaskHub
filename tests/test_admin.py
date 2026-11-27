from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app as fastapi_app
from app.models.user import User, UserRole
from tests.helpers import create_workspace_and_project, login_as, user_id_of


async def promote_to_admin(email: str) -> None:
    async with fastapi_app.state.test_sessionmaker() as session:
        user = await session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = UserRole.ADMIN
        await session.commit()


async def test_admin_endpoint_rejects_regular_user(client: AsyncClient) -> None:
    headers = await login_as(client, "member@example.com")
    response = await client.get("/api/v1/admin/workspaces", headers=headers)
    assert response.status_code == 403


async def test_admin_can_list_every_workspace(client: AsyncClient) -> None:
    owner = await login_as(client, "owner@example.com")
    await client.post("/api/v1/workspaces", json={"name": "Team A"}, headers=owner)

    admin = await login_as(client, "admin@example.com")
    await promote_to_admin("admin@example.com")
    admin = await login_as(client, "admin@example.com")

    response = await client.get("/api/v1/admin/workspaces", headers=admin)
    assert response.status_code == 200
    assert [workspace["name"] for workspace in response.json()["items"]] == ["Team A"]
    assert response.json()["total"] == 1


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        ("patch_workspace", 200),
        ("delete_workspace", 204),
        ("invite_member", 201),
        ("update_member_role", 200),
        ("remove_member", 204),
        ("create_project", 201),
        ("patch_project", 200),
        ("archive_project", 200),
        ("delete_project", 204),
        ("create_task", 201),
        ("patch_task", 200),
        ("delete_task", 204),
        ("create_label", 201),
        ("patch_label", 200),
        ("delete_label", 204),
        ("attach_label", 204),
        ("detach_label", 204),
        ("create_comment", 201),
    ],
)
async def test_admin_can_perform_write_actions_without_membership(
    client: AsyncClient, action: str, expected_status: int
) -> None:
    owner = await login_as(client, "ws-owner@example.com")
    member_headers = await login_as(client, "ws-member@example.com")
    member_id = await user_id_of(client, member_headers)
    await login_as(client, "invitee@example.com")

    workspace_id, project_id = await create_workspace_and_project(client, owner)
    invited = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "ws-member@example.com", "role": "VIEWER"},
        headers=owner,
    )
    assert invited.status_code == 201

    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Seed task"},
        headers=owner,
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]

    label_resp = await client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "bug", "color": "#ff0000"},
        headers=owner,
    )
    assert label_resp.status_code == 201
    label_id = label_resp.json()["id"]

    if action == "detach_label":
        attached = await client.post(
            f"/api/v1/tasks/{task_id}/labels/{label_id}",
            headers=owner,
        )
        assert attached.status_code == 204

    await login_as(client, "super-admin@example.com")
    await promote_to_admin("super-admin@example.com")
    admin = await login_as(client, "super-admin@example.com")

    requests: dict[str, tuple[str, str, dict[str, Any] | None]] = {
        "patch_workspace": ("PATCH", f"/api/v1/workspaces/{workspace_id}", {"name": "Renamed"}),
        "delete_workspace": ("DELETE", f"/api/v1/workspaces/{workspace_id}", None),
        "invite_member": (
            "POST",
            f"/api/v1/workspaces/{workspace_id}/members",
            {"email": "invitee@example.com", "role": "EDITOR"},
        ),
        "update_member_role": (
            "PATCH",
            f"/api/v1/workspaces/{workspace_id}/members/{member_id}",
            {"role": "EDITOR"},
        ),
        "remove_member": ("DELETE", f"/api/v1/workspaces/{workspace_id}/members/{member_id}", None),
        "create_project": ("POST", f"/api/v1/workspaces/{workspace_id}/projects", {"name": "P2"}),
        "patch_project": ("PATCH", f"/api/v1/projects/{project_id}", {"name": "P1-edit"}),
        "archive_project": ("POST", f"/api/v1/projects/{project_id}/archive", None),
        "delete_project": ("DELETE", f"/api/v1/projects/{project_id}", None),
        "create_task": ("POST", f"/api/v1/projects/{project_id}/tasks", {"title": "T2"}),
        "patch_task": ("PATCH", f"/api/v1/tasks/{task_id}", {"title": "T1-edit"}),
        "delete_task": ("DELETE", f"/api/v1/tasks/{task_id}", None),
        "create_label": (
            "POST",
            f"/api/v1/projects/{project_id}/labels",
            {"name": "feat", "color": "#00ff00"},
        ),
        "patch_label": ("PATCH", f"/api/v1/labels/{label_id}", {"name": "bugfix"}),
        "delete_label": ("DELETE", f"/api/v1/labels/{label_id}", None),
        "attach_label": ("POST", f"/api/v1/tasks/{task_id}/labels/{label_id}", None),
        "detach_label": ("DELETE", f"/api/v1/tasks/{task_id}/labels/{label_id}", None),
        "create_comment": (
            "POST",
            f"/api/v1/tasks/{task_id}/comments",
            {"content": "Admin comment"},
        ),
    }

    method, url, json_body = requests[action]
    act_response = await client.request(method, url, json=json_body, headers=admin)
    assert 200 <= act_response.status_code < 300
    assert act_response.status_code == expected_status
