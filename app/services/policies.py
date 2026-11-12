from typing import Protocol

from app.core.constants import COMMENT_NOT_OWNER_MESSAGE, PROJECT_ARCHIVED_MESSAGE
from app.core.exceptions import ConflictError, ForbiddenError
from app.models.enums import ProjectStatus, WorkspaceMemberRole
from app.models.project import Project
from app.models.user import User


class WorkspaceAccess(Protocol):
    @property
    def effective_role(self) -> WorkspaceMemberRole: ...


class TaskAccess(Protocol):
    @property
    def workspace(self) -> WorkspaceAccess: ...


def ensure_project_active(project: Project) -> None:
    if project.status == ProjectStatus.ARCHIVED:
        raise ConflictError(PROJECT_ARCHIVED_MESSAGE)


def ensure_comment_deletion_allowed(access: TaskAccess, user: User, author_id: int) -> None:
    if (
        author_id != user.id
        and access.workspace.effective_role.rank < WorkspaceMemberRole.OWNER.rank
    ):
        raise ForbiddenError(COMMENT_NOT_OWNER_MESSAGE)
