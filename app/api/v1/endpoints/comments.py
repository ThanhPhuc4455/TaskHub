from typing import Annotated, cast

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CacheDep,
    CommentServiceDep,
    CurrentUser,
    PaginationDep,
    require_comment_role,
    require_task_role,
)
from app.api.responses import RBAC_RESPONSES
from app.core.cache import invalidate_task_cache
from app.models.comment import Comment
from app.models.enums import WorkspaceMemberRole
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.page import PageResponse
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
    cache: CacheDep,
) -> Comment:
    comment = await service.create(task, current_user, payload)
    await invalidate_task_cache(cache, task.project.id)
    return comment


@router.get("/tasks/{task_id}/comments", response_model=PageResponse[CommentRead])
async def list_comments(
    task: TaskViewer, service: CommentServiceDep, pagination: PaginationDep
) -> PageResponse[CommentRead]:
    comments, total = await service.list_comments(task, pagination)
    return PageResponse.from_result(
        cast(list[CommentRead], comments), total, pagination.page, pagination.limit
    )


@router.delete("/tasks/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    access: CommentViewer,
    current_user: CurrentUser,
    service: CommentServiceDep,
    cache: CacheDep,
) -> None:
    await service.delete(access, current_user)
    await invalidate_task_cache(cache, access.task.project.id)
