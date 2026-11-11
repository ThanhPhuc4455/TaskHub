import enum


class UserRole(enum.StrEnum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class WorkspaceMemberRole(enum.StrEnum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

    @property
    def rank(self) -> int:
        return _ROLE_RANK[self]


_ROLE_RANK: dict[WorkspaceMemberRole, int] = {
    WorkspaceMemberRole.VIEWER: 1,
    WorkspaceMemberRole.EDITOR: 2,
    WorkspaceMemberRole.OWNER: 3,
}


class ProjectStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TaskStatus(enum.StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(enum.StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"
