from httpx import AsyncClient

from tests.helpers import login_as

WS = "/api/v1/workspaces"


async def project_for(client: AsyncClient, headers: dict[str, str], name: str = "Workspace") -> int:
    workspace = await client.post(WS, json={"name": name}, headers=headers)
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]
    project = await client.post(
        f"{WS}/{workspace_id}/projects", json={"name": "Project"}, headers=headers
    )
    assert project.status_code == 201
    return int(project.json()["id"])


async def test_task_crud_filters_and_pagination(client: AsyncClient) -> None:
    owner = await login_as(client, "task-owner@example.com")
    project_id = await project_for(client, owner)

    first = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "First", "priority": "HIGH"},
        headers=owner,
    )
    second = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Second"},
        headers=owner,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    rejected_client_status = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Client status must be server-owned", "status": "DONE"},
        headers=owner,
    )
    assert rejected_client_status.status_code == 422
    assert second.json()["status"] == "TODO"
    assert first.json()["labels"] == []
    task_id = first.json()["id"]

    listed = await client.get(
        f"/api/v1/projects/{project_id}/tasks?priority=HIGH&page=1&limit=1",
        headers=owner,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == task_id

    updated = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"description": None, "status": "IN_PROGRESS"},
        headers=owner,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "IN_PROGRESS"


async def test_task_rbac_assignee_and_archived_project(client: AsyncClient) -> None:
    owner = await login_as(client, "task-owner-2@example.com")
    viewer = await login_as(client, "task-viewer@example.com")
    project_id = await project_for(client, owner, "RBAC workspace")

    workspace_id = (await client.get(f"/api/v1/projects/{project_id}", headers=owner)).json()[
        "workspace_id"
    ]
    invited = await client.post(
        f"{WS}/{workspace_id}/members",
        json={"email": "task-viewer@example.com", "role": "VIEWER"},
        headers=owner,
    )
    assert invited.status_code == 201

    forbidden = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "No"},
        headers=viewer,
    )
    assert forbidden.status_code == 403

    bad_assignee = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Bad assignee", "assignee_id": 999999},
        headers=owner,
    )
    assert bad_assignee.status_code == 400
    assert "workspace member" in bad_assignee.json()["detail"]

    archived = await client.post(f"/api/v1/projects/{project_id}/archive", headers=owner)
    assert archived.status_code == 200
    blocked = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Blocked"},
        headers=owner,
    )
    assert blocked.status_code == 409


async def test_labels_and_comments_enforce_project_and_comment_rules(
    client: AsyncClient,
) -> None:
    owner = await login_as(client, "content-owner@example.com")
    editor = await login_as(client, "content-editor@example.com")
    viewer = await login_as(client, "content-viewer@example.com")
    other = await login_as(client, "content-other@example.com")
    project_id = await project_for(client, owner, "Content workspace")
    project = await client.get(f"/api/v1/projects/{project_id}", headers=owner)
    workspace_id = project.json()["workspace_id"]
    invited = await client.post(
        f"{WS}/{workspace_id}/members",
        json={"email": "content-editor@example.com", "role": "EDITOR"},
        headers=owner,
    )
    assert invited.status_code == 201
    for email, role in (
        ("content-viewer@example.com", "VIEWER"),
        ("content-other@example.com", "EDITOR"),
    ):
        invited = await client.post(
            f"{WS}/{workspace_id}/members",
            json={"email": email, "role": role},
            headers=owner,
        )
        assert invited.status_code == 201

    task = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Commented task"},
        headers=editor,
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    label = await client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "backend", "color": "#12abef"},
        headers=editor,
    )
    assert label.status_code == 201
    label_id = label.json()["id"]
    viewer_label = await client.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "viewer-label"},
        headers=viewer,
    )
    assert viewer_label.status_code == 403
    assert (
        await client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=editor)
    ).status_code == 204
    duplicate = await client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=editor)
    assert duplicate.status_code == 409
    assert (
        await client.delete(f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=editor)
    ).status_code == 204
    missing_detach = await client.delete(
        f"/api/v1/tasks/{task_id}/labels/{label_id}", headers=editor
    )
    assert missing_detach.status_code == 404

    comment = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Looks good"},
        headers=editor,
    )
    assert comment.status_code == 201
    comment_id = comment.json()["id"]
    assert comment.json()["author"]["email"] == "content-editor@example.com"

    viewer_comment = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "viewer cannot comment"},
        headers=viewer,
    )
    assert viewer_comment.status_code == 403
    denied = await client.delete(f"/api/v1/tasks/{task_id}/comments/{comment_id}", headers=other)
    assert denied.status_code == 403
    owner_deleted = await client.delete(
        f"/api/v1/tasks/{task_id}/comments/{comment_id}", headers=owner
    )
    assert owner_deleted.status_code == 204

    editor_comment = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "editor comment"},
        headers=editor,
    )
    assert editor_comment.status_code == 201
    deleted = await client.delete(
        f"/api/v1/tasks/{task_id}/comments/{editor_comment.json()['id']}",
        headers=editor,
    )
    assert deleted.status_code == 204
