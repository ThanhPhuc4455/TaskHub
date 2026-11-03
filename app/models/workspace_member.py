
import enum

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship      
from app.models.base import Base
from app.models.user import User
from app.models.workspace import Workspace


class WorkspaceMemberRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[WorkspaceMemberRole] = mapped_column(
        Enum(
            WorkspaceMemberRole,
            name="workspace_member_role",
            native_enum=False,
        ),
        default=WorkspaceMemberRole.MEMBER,
        nullable=False,
    )
    workspace: Mapped["Workspace"] = relationship(
        back_populates="memberships",
    )

    user: Mapped["User"] = relationship(
        back_populates="workspace_memberships",
    )
