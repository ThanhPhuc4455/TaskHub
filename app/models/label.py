from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import COLOR_MAX_LENGTH, LABEL_NAME_MAX_LENGTH
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task

task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "label_id",
        Integer,
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class Label(Base):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_label_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(LABEL_NAME_MAX_LENGTH), nullable=False)

    color: Mapped[str] = mapped_column(String(COLOR_MAX_LENGTH), default="#808080", nullable=False)

    project: Mapped["Project"] = relationship(back_populates="labels")

    tasks: Mapped[list["Task"]] = relationship(
        secondary=task_labels,
        back_populates="labels",
    )
