import logging
from typing import Protocol

from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


class NotificationService(Protocol):
    async def notify_task_assigned(
        self,
        *,
        recipient_email: str,
        task_title: str,
        project_name: str,
        assigner_name: str,
    ) -> None: ...


class LoggingNotificationService:
    async def notify_task_assigned(
        self,
        *,
        recipient_email: str,
        task_title: str,
        project_name: str,
        assigner_name: str,
    ) -> None:
        logger.info(
            "Task assignment notification: task=%s project=%s assigner=%s",
            task_title,
            project_name,
            assigner_name,
        )


async def notify_task_assigned_safely(
    notification: NotificationService,
    *,
    recipient_email: str,
    task_title: str,
    project_name: str,
    assigner_name: str,
) -> None:
    try:
        await notification.notify_task_assigned(
            recipient_email=recipient_email,
            task_title=task_title,
            project_name=project_name,
            assigner_name=assigner_name,
        )
    except Exception:
        logger.exception("Task assignment notification failed")


def queue_assignment_notification(
    background_tasks: BackgroundTasks,
    notification: NotificationService,
    *,
    recipient_email: str,
    task_title: str,
    project_name: str,
    assigner_name: str,
) -> None:
    background_tasks.add_task(
        notify_task_assigned_safely,
        notification,
        recipient_email=recipient_email,
        task_title=task_title,
        project_name=project_name,
        assigner_name=assigner_name,
    )
