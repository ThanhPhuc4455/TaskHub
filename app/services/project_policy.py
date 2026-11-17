from app.core.exceptions import BadRequestError
from app.core.messages import PROJECT_ARCHIVED_MESSAGE
from app.models.enums import ProjectStatus
from app.models.project import Project


def ensure_project_active(project: Project) -> None:
    if project.status == ProjectStatus.ARCHIVED:
        raise BadRequestError(PROJECT_ARCHIVED_MESSAGE)
