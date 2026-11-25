from fastapi import APIRouter, status

from app.api.deps import (
    CommentServiceDep,
    CommentViewer,
    CurrentUser,
    PaginationDep,
    TaskEditor,
    TaskViewer,
)
from app.api.responses import RBAC_RESPONSES
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.page import PageResponse

router = APIRouter(tags=["comments"], responses=RBAC_RESPONSES)


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


@router.get("/tasks/{task_id}/comments", response_model=PageResponse[CommentRead])
async def list_comments(
    task: TaskViewer, service: CommentServiceDep, pagination: PaginationDep
) -> PageResponse[CommentRead]:
    result = await service.list_comments(task, pagination)
    return PageResponse.from_page_result(result, pagination)


@router.delete("/tasks/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    access: CommentViewer,
    current_user: CurrentUser,
    service: CommentServiceDep,
) -> None:
    await service.delete(access, current_user)
