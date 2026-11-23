import logging
from email.message import EmailMessage
from typing import Protocol

import aiosmtplib
from fastapi import BackgroundTasks

from app.core.config import Settings

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
        logger.info("Task assignment notification disabled")


class SmtpNotificationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def notify_task_assigned(
        self,
        *,
        recipient_email: str,
        task_title: str,
        project_name: str,
        assigner_name: str,
    ) -> None:
        subject = f"Task assigned: {task_title.replace(chr(13), '').replace(chr(10), '')}"
        message = EmailMessage()
        message["From"] = self.settings.smtp_from_address or ""
        message["To"] = recipient_email
        message["Subject"] = subject
        message.set_content(
            f"Task: {task_title}\nProject: {project_name}\nAssigned by: {assigner_name}"
        )
        username = self.settings.smtp_username or None
        password = (
            self.settings.smtp_password.get_secret_value()
            if username and self.settings.smtp_password
            else None
        )
        await aiosmtplib.send(
            message,
            hostname=self.settings.smtp_host,
            port=self.settings.smtp_port,
            username=username,
            password=password,
            use_tls=self.settings.smtp_use_tls,
            start_tls=self.settings.smtp_start_tls,
            timeout=self.settings.smtp_timeout_seconds,
        )


async def notify_task_assigned_safely(
    notification: NotificationService,
    *,
    recipient_email: str,
    task_id: int,
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
        logger.info("Task assignment notification sent: task_id=%s", task_id)
    except Exception:
        logger.exception("Task assignment notification failed: task_id=%s", task_id)


def queue_assignment_notification(
    background_tasks: BackgroundTasks,
    notification: NotificationService,
    *,
    task_id: int,
    recipient_email: str,
    task_title: str,
    project_name: str,
    assigner_name: str,
) -> None:
    background_tasks.add_task(
        notify_task_assigned_safely,
        notification,
        task_id=task_id,
        recipient_email=recipient_email,
        task_title=task_title,
        project_name=project_name,
        assigner_name=assigner_name,
    )
