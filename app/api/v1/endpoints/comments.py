from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CommentServiceDep,
    CurrentUser,
    PaginationDep,
    require_comment_role,
    require_task_role,
)
from app.api.responses import RBAC_RESPONSES
from app.models.comment import Comment
from app.models.enums import WorkspaceMemberRole
from app.schemas.comment import CommentCreate, CommentPageResponse, CommentRead
from app.services.comment_service import CommentAccessContext
from app.services.task_service import TaskAccessContext

router = APIRouter(tags=["comments"], responses=RBAC_RESPONSES)

TaskViewer = Annotated[
    TaskAccessContext,
    Depends(require_task_role(WorkspaceMemberRole.VIEWER)),
]
TaskEditor = Annotated[
    TaskAccessContext,
    Depends(require_task_role(WorkspaceMemberRole.EDITOR)),
]
CommentViewer = Annotated[
    CommentAccessContext,
    Depends(require_comment_role(WorkspaceMemberRole.VIEWER)),
]


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    payload: CommentCreate,
    task: TaskEditor,
    current_user: CurrentUser,
    service: CommentServiceDep,
) -> Comment:
    return await service.create(task, current_user, payload)


@router.get("/tasks/{task_id}/comments", response_model=CommentPageResponse)
async def list_comments(
    task: TaskViewer, service: CommentServiceDep, pagination: PaginationDep
) -> CommentPageResponse:
    comments, total = await service.list_comments(task, pagination)
    return CommentPageResponse(
        items=comments, total=total, page=pagination.page, limit=pagination.limit
    )


@router.delete("/tasks/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    access: CommentViewer,
    current_user: CurrentUser,
    service: CommentServiceDep,
) -> None:
    await service.delete(access, current_user)
