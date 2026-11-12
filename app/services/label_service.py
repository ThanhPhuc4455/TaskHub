from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.core.constants import (
    LABEL_ALREADY_ATTACHED_MESSAGE,
    LABEL_ALREADY_EXISTS_MESSAGE,
    LABEL_PROJECT_MISMATCH_MESSAGE,
    PROJECT_ARCHIVED_MESSAGE,
)
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import Pagination
from app.models.enums import ProjectStatus
from app.models.label import Label
from app.models.project import Project
from app.repositories.label_repository import LabelRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.label import LabelCreate, LabelUpdate
from app.services.project_service import ProjectAccessContext
from app.services.task_service import TaskAccessContext
from app.services.workspace_service import WorkspaceAccessContext


@dataclass(frozen=True)
class LabelAccessContext:
    label: Label
    project: Project
    workspace: WorkspaceAccessContext


class LabelService:
    def __init__(self, labels: LabelRepository, tasks: TaskRepository) -> None:
        self._labels = labels
        self._tasks = tasks

    @staticmethod
    def _ensure_active(project: Project) -> None:
        if project.status == ProjectStatus.ARCHIVED:
            raise BadRequestError(PROJECT_ARCHIVED_MESSAGE)

    async def create(self, access: ProjectAccessContext, payload: LabelCreate) -> Label:
        self._ensure_active(access.project)
        try:
            return await self._labels.create(
                project_id=access.project.id,
                name=payload.name,
                color=payload.color,
            )
        except IntegrityError as exc:
            await self._labels.rollback()
            raise ConflictError(LABEL_ALREADY_EXISTS_MESSAGE) from exc

    async def list_labels(
        self, access: ProjectAccessContext, pagination: Pagination
    ) -> list[Label]:
        return await self._labels.list_by_project(
            access.project.id, offset=pagination.offset, limit=pagination.limit
        )

    async def update(self, access: LabelAccessContext, payload: LabelUpdate) -> Label:
        self._ensure_active(access.project)
        try:
            return await self._labels.update(access.label, payload.model_dump(exclude_unset=True))
        except IntegrityError as exc:
            await self._labels.rollback()
            raise ConflictError(LABEL_ALREADY_EXISTS_MESSAGE) from exc

    async def delete(self, access: LabelAccessContext) -> None:
        self._ensure_active(access.project)
        await self._labels.delete(access.label)

    async def attach(self, task: TaskAccessContext, label: Label) -> None:
        self._ensure_active(task.project)
        if label.project_id != task.project.id:
            raise BadRequestError(LABEL_PROJECT_MISMATCH_MESSAGE)
        try:
            await self._tasks.attach_label(task.task.id, label.id)
        except IntegrityError as exc:
            await self._tasks.rollback()
            raise ConflictError(LABEL_ALREADY_ATTACHED_MESSAGE) from exc

    async def detach(self, task: TaskAccessContext, label: Label) -> None:
        self._ensure_active(task.project)
        if label.project_id != task.project.id:
            raise BadRequestError(LABEL_PROJECT_MISMATCH_MESSAGE)
        if await self._tasks.detach_label(task.task.id, label.id) == 0:
            raise NotFoundError("Task label", label.id)
