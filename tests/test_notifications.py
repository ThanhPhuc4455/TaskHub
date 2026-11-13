from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.deps import get_cache_backend, get_notification_service
from app.main import app as fastapi_app
from tests.helpers import login_as, user_id_of


class FakeNotificationService:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, str]] = []
        self.fail = fail

    async def notify_task_assigned(
        self,
        *,
        recipient_email: str,
        task_title: str,
        project_name: str,
        assigner_name: str,
    ) -> None:
        if self.fail:
            raise RuntimeError("notification failed")
        self.calls.append(
            {
                "recipient_email": recipient_email,
                "task_title": task_title,
                "project_name": project_name,
                "assigner_name": assigner_name,
            }
        )


@pytest_asyncio.fixture
async def notification_service(client: AsyncClient) -> AsyncIterator[FakeNotificationService]:
    service = FakeNotificationService()
    fastapi_app.dependency_overrides[get_notification_service] = lambda: service
    yield service
    fastapi_app.dependency_overrides.pop(get_notification_service, None)


async def setup_project(client: AsyncClient) -> tuple[dict[str, str], dict[str, str], int, int]:
    owner = await login_as(client, "notification-owner@example.com")
    assignee = await login_as(client, "notification-assignee@example.com")
    workspace = await client.post(
        "/api/v1/workspaces", json={"name": "Notification workspace"}, headers=owner
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]
    invited = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "notification-assignee@example.com", "role": "EDITOR"},
        headers=owner,
    )
    assert invited.status_code == 201
    project = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        json={"name": "Notification project"},
        headers=owner,
    )
    assert project.status_code == 201
    return owner, assignee, int(project.json()["id"]), await user_id_of(client, assignee)


async def test_create_assigned_task_notifies_once(
    client: AsyncClient, notification_service: FakeNotificationService
) -> None:
    owner, _, project_id, assignee_id = await setup_project(client)

    response = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Assigned task", "assignee_id": assignee_id},
        headers=owner,
    )

    assert response.status_code == 201
    assert notification_service.calls == [
        {
            "recipient_email": "notification-assignee@example.com",
            "task_title": "Assigned task",
            "project_name": "Notification project",
            "assigner_name": "User",
        }
    ]


async def test_create_task_does_not_notify_without_external_assignee(
    client: AsyncClient, notification_service: FakeNotificationService
) -> None:
    owner, _, project_id, _ = await setup_project(client)
    owner_id = await user_id_of(client, owner)

    no_assignee = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Unassigned task"},
        headers=owner,
    )
    self_assigned = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Self assigned", "assignee_id": owner_id},
        headers=owner,
    )

    assert no_assignee.status_code == self_assigned.status_code == 201
    assert notification_service.calls == []


async def test_task_reassignment_notifies_only_for_new_assignee(
    client: AsyncClient, notification_service: FakeNotificationService
) -> None:
    owner, assignee, project_id, first_assignee_id = await setup_project(client)
    second_assignee = await login_as(client, "notification-second@example.com")
    workspace_id = (await client.get(f"/api/v1/projects/{project_id}", headers=owner)).json()[
        "workspace_id"
    ]
    invited = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "notification-second@example.com", "role": "EDITOR"},
        headers=owner,
    )
    assert invited.status_code == 201
    second_assignee_id = await user_id_of(client, second_assignee)
    task = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Reassign me", "assignee_id": first_assignee_id},
        headers=owner,
    )
    assert task.status_code == 201
    notification_service.calls.clear()

    same = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}",
        json={"assignee_id": first_assignee_id},
        headers=owner,
    )
    changed = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}",
        json={"assignee_id": second_assignee_id},
        headers=owner,
    )
    unassigned = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}", json={"assignee_id": None}, headers=owner
    )

    assert same.status_code == changed.status_code == unassigned.status_code == 200
    assert len(notification_service.calls) == 1
    assert notification_service.calls[0]["recipient_email"] == "notification-second@example.com"


async def test_notification_failure_does_not_fail_task_creation(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    service = FakeNotificationService(fail=True)
    fastapi_app.dependency_overrides[get_notification_service] = lambda: service
    owner, _, project_id, assignee_id = await setup_project(client)

    with caplog.at_level("ERROR"):
        response = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": "Notification failure", "assignee_id": assignee_id},
            headers=owner,
        )

    assert response.status_code == 201
    assert "Task assignment notification failed" in caplog.text
    fastapi_app.dependency_overrides.pop(get_notification_service, None)
    fastapi_app.dependency_overrides.pop(get_cache_backend, None)
