from app.core.exceptions import ConflictError, ForbiddenError
from app.core.messages import COMMENT_NOT_OWNER_MESSAGE, PROJECT_ARCHIVED_MESSAGE
from app.models.enums import ProjectStatus, WorkspaceMemberRole
from app.models.project import Project


def ensure_project_active(project: Project) -> None:
    if project.status == ProjectStatus.ARCHIVED:
        raise ConflictError(PROJECT_ARCHIVED_MESSAGE)


def ensure_comment_deletion_allowed(
    author_id: int, user_id: int, effective_role: WorkspaceMemberRole
) -> None:
    if author_id != user_id and effective_role.rank < WorkspaceMemberRole.OWNER.rank:
        raise ForbiddenError(COMMENT_NOT_OWNER_MESSAGE)
