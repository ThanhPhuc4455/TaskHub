from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.core.cache import TaskCacheInvalidator
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.messages import (
    LABEL_ALREADY_ATTACHED_MESSAGE,
    LABEL_ALREADY_EXISTS_MESSAGE,
    LABEL_PROJECT_MISMATCH_MESSAGE,
)
from app.core.pagination import PageResult, Pagination
from app.models.enums import WorkspaceMemberRole
from app.models.label import Label
from app.models.project import Project
from app.models.workspace import Workspace
from app.repositories.label_repository import LabelRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.label import LabelCreate, LabelUpdate
from app.services.project_policy import ensure_project_active
from app.services.project_service import ProjectAccessContext
from app.services.task_service import TaskAccessContext


@dataclass(frozen=True)
class LabelAccessContext:
    label: Label
    project: Project
    workspace: Workspace
    effective_role: WorkspaceMemberRole


class LabelService:
    def __init__(
        self,
        labels: LabelRepository,
        tasks: TaskRepository,
        invalidator: TaskCacheInvalidator | None = None,
    ) -> None:
        self._labels = labels
        self._tasks = tasks
        self._invalidator = invalidator

    async def _invalidate(self, project_id: int) -> None:
        if self._invalidator is not None:
            await self._invalidator.invalidate(project_id)

    async def create(self, access: ProjectAccessContext, payload: LabelCreate) -> Label:
        ensure_project_active(access.project)
        try:
            label = await self._labels.create(
                project_id=access.project.id,
                name=payload.name,
                color=payload.color,
            )
            await self._invalidate(access.project.id)
            return label
        except IntegrityError as exc:
            await self._labels.rollback()
            raise ConflictError(LABEL_ALREADY_EXISTS_MESSAGE) from exc

    async def list_labels(
        self, access: ProjectAccessContext, pagination: Pagination
    ) -> PageResult[Label]:
        return await self._labels.list_by_project(access.project.id, pagination)

    async def update(self, access: LabelAccessContext, payload: LabelUpdate) -> Label:
        ensure_project_active(access.project)
        try:
            label = await self._labels.update(access.label, payload.model_dump(exclude_unset=True))
            await self._invalidate(access.project.id)
            return label
        except IntegrityError as exc:
            await self._labels.rollback()
            raise ConflictError(LABEL_ALREADY_EXISTS_MESSAGE) from exc

    async def delete(self, access: LabelAccessContext) -> None:
        ensure_project_active(access.project)
        await self._labels.delete(access.label)
        await self._invalidate(access.project.id)

    async def attach(self, task: TaskAccessContext, label_id: int) -> None:
        ensure_project_active(task.project)
        label = await self._labels.get(label_id)
        if label is None:
            raise NotFoundError("Label", label_id)
        if label.project_id != task.project.id:
            raise BadRequestError(LABEL_PROJECT_MISMATCH_MESSAGE)
        if await self._tasks.attach_label(task.task.id, label.id) == 0:
            raise ConflictError(LABEL_ALREADY_ATTACHED_MESSAGE)
        await self._invalidate(task.project.id)

    async def detach(self, task: TaskAccessContext, label_id: int) -> None:
        ensure_project_active(task.project)
        label = await self._labels.get(label_id)
        if label is None:
            raise NotFoundError("Label", label_id)
        if label.project_id != task.project.id:
            raise BadRequestError(LABEL_PROJECT_MISMATCH_MESSAGE)
        if await self._tasks.detach_label(task.task.id, label.id) == 0:
            raise NotFoundError("Task label", label.id)
        await self._invalidate(task.project.id)
