from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import aiosmtplib
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.deps import get_cache_backend, get_notification_service
from app.core.config import Settings
from app.main import app as fastapi_app
from app.services.notification_service import (
    LoggingNotificationService,
    SmtpNotificationService,
    notify_task_assigned_safely,
)
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
    self_assigned = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}",
        json={"assignee_id": await user_id_of(client, owner)},
        headers=owner,
    )
    unassigned = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}", json={"assignee_id": None}, headers=owner
    )

    assert (
        same.status_code
        == changed.status_code
        == self_assigned.status_code
        == unassigned.status_code
        == 200
    )
    assert len(notification_service.calls) == 1
    assert notification_service.calls[0]["recipient_email"] == "notification-second@example.com"


async def test_update_task_does_not_notify_when_assigning_to_current_user(
    client: AsyncClient, notification_service: FakeNotificationService
) -> None:
    owner, _, project_id, assignee_id = await setup_project(client)
    task = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Self assign on update", "assignee_id": assignee_id},
        headers=owner,
    )
    assert task.status_code == 201
    notification_service.calls.clear()

    response = await client.patch(
        f"/api/v1/tasks/{task.json()['id']}",
        json={"assignee_id": await user_id_of(client, owner)},
        headers=owner,
    )

    assert response.status_code == 200
    assert notification_service.calls == []


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


async def test_smtp_sender_sends_sanitized_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        secret_key="test",
        smtp_enabled=True,
        smtp_host="127.0.0.1",
        smtp_from_address="taskhub@example.local",
    )
    sender = SmtpNotificationService(settings)
    send = AsyncMock()
    monkeypatch.setattr(aiosmtplib, "send", send)

    await sender.notify_task_assigned(
        recipient_email="recipient@example.local",
        task_title="Fix bug\r\nBcc: attacker@example.local",
        project_name="Project",
        assigner_name="Owner",
    )

    send.assert_awaited_once()
    call = send.await_args
    assert call is not None
    message = call.args[0]
    assert "\r" not in message["Subject"]
    assert "\n" not in message["Subject"]
    assert message["To"] == "recipient@example.local"


async def test_smtp_failure_is_safe_and_does_not_log_email(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        secret_key="test",
        smtp_enabled=True,
        smtp_host="127.0.0.1",
        smtp_from_address="taskhub@example.local",
    )
    sender = SmtpNotificationService(settings)
    monkeypatch.setattr(aiosmtplib, "send", AsyncMock(side_effect=TimeoutError))

    with caplog.at_level("ERROR"):
        await notify_task_assigned_safely(
            sender,
            task_id=42,
            recipient_email="private@example.local",
            task_title="Private task",
            project_name="Project",
            assigner_name="Owner",
        )

    assert "private@example.local" not in caplog.text


async def test_disabled_notification_does_not_call_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    send = AsyncMock()
    monkeypatch.setattr(aiosmtplib, "send", send)
    service = LoggingNotificationService()
    await service.notify_task_assigned(
        recipient_email="recipient@example.local",
        task_title="Task",
        project_name="Project",
        assigner_name="Owner",
    )
    send.assert_not_awaited()
