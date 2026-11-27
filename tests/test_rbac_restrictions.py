import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.main import app as fastapi_app
from app.models.user import User, UserRole
from tests.helpers import create_workspace_and_project, login_as


async def promote_to_admin(email: str) -> None:
    async with fastapi_app.state.test_sessionmaker() as session:
        user = await session.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = UserRole.ADMIN
        await session.commit()


async def _setup_workspace_with_project_and_task(
    client: AsyncClient,
) -> tuple[dict[str, str], int, int, int, int]:
    """Create owner, workspace, project, task, and a comment by owner.

    Return (owner_headers, workspace_id, project_id, task_id, comment_id).
    """
    owner = await login_as(client, "rbac-owner@example.com")
    workspace_id, project_id = await create_workspace_and_project(client, owner)
    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "RBAC task"},
        headers=owner,
    )
    assert task_resp.status_code == 201
    task_id = task_resp.json()["id"]
    comment_resp = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Owner comment"},
        headers=owner,
    )
    assert comment_resp.status_code == 201
    comment_id = comment_resp.json()["id"]
    return owner, workspace_id, project_id, task_id, comment_id


@pytest.mark.parametrize(
    "action",
    ["archive_project", "delete_project"],
)
async def test_viewer_cannot_archive_or_delete_project(client: AsyncClient, action: str) -> None:
    owner, workspace_id, project_id, _, _ = await _setup_workspace_with_project_and_task(client)
    viewer = await login_as(client, "rbac-viewer@example.com")
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "rbac-viewer@example.com", "role": "VIEWER"},
        headers=owner,
    )

    if action == "archive_project":
        resp = await client.post(f"/api/v1/projects/{project_id}/archive", headers=viewer)
    else:
        resp = await client.delete(f"/api/v1/projects/{project_id}", headers=viewer)
    assert resp.status_code == 403


@pytest.mark.parametrize(
    ("role", "is_author", "expected_status"),
    [
        ("VIEWER", False, 403),
        ("EDITOR", False, 403),
        ("EDITOR", True, 204),
    ],
    ids=["viewer-not-author", "editor-not-author", "editor-is-author"],
)
async def test_comment_delete_rbac(
    client: AsyncClient, role: str, is_author: bool, expected_status: int
) -> None:
    (
        owner,
        workspace_id,
        project_id,
        task_id,
        owner_comment_id,
    ) = await _setup_workspace_with_project_and_task(client)

    actor = await login_as(client, f"rbac-{role.lower()}-actor@example.com")
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": f"rbac-{role.lower()}-actor@example.com", "role": role},
        headers=owner,
    )

    if is_author:
        own_comment = await client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "My own comment"},
            headers=actor,
        )
        assert own_comment.status_code == 201
        target_comment_id = own_comment.json()["id"]
    else:
        target_comment_id = owner_comment_id

    resp = await client.delete(
        f"/api/v1/tasks/{task_id}/comments/{target_comment_id}", headers=actor
    )
    assert resp.status_code == expected_status


async def test_owner_can_delete_others_comment(client: AsyncClient) -> None:
    owner, workspace_id, _, task_id, _ = await _setup_workspace_with_project_and_task(client)
    editor = await login_as(client, "rbac-editor-comment@example.com")
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "rbac-editor-comment@example.com", "role": "EDITOR"},
        headers=owner,
    )
    comment_resp = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Editor comment"},
        headers=editor,
    )
    assert comment_resp.status_code == 201
    comment_id = comment_resp.json()["id"]

    resp = await client.delete(f"/api/v1/tasks/{task_id}/comments/{comment_id}", headers=owner)
    assert resp.status_code == 204


async def test_admin_can_delete_others_comment(client: AsyncClient) -> None:
    _, workspace_id, _, task_id, owner_comment_id = await _setup_workspace_with_project_and_task(
        client
    )
    await login_as(client, "rbac-admin-comment@example.com")
    await promote_to_admin("rbac-admin-comment@example.com")
    admin = await login_as(client, "rbac-admin-comment@example.com")

    resp = await client.delete(
        f"/api/v1/tasks/{task_id}/comments/{owner_comment_id}", headers=admin
    )
    assert resp.status_code == 204
