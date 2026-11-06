import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


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


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    role: Mapped[WorkspaceMemberRole] = mapped_column(
        Enum(
            WorkspaceMemberRole,
            name="workspace_member_role",
            native_enum=False,
            length=20,
        ),
        default=WorkspaceMemberRole.VIEWER,
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="memberships",
    )

    user: Mapped["User"] = relationship(
        back_populates="workspace_memberships",
    )
