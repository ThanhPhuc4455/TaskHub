from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CacheDep, CurrentUser, UserServiceDep, get_task_repository
from app.api.responses import AUTH_RESPONSES, USER_RESPONSES
from app.core.cache import invalidate_task_cache
from app.models.user import User
from app.repositories.task_repository import TaskRepository
from app.schemas.user import ChangePasswordRequest, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], responses=AUTH_RESPONSES)


@router.get("/me", response_model=UserRead, summary="Get the current user profile")
async def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserRead, summary="Update the current user profile")
async def update_me(
    payload: UserUpdate,
    current_user: CurrentUser,
    service: UserServiceDep,
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    cache: CacheDep,
) -> User:
    project_ids = await tasks.project_ids_by_assignee(current_user.id)
    user = await service.update_profile(current_user, payload)
    for project_id in project_ids:
        await invalidate_task_cache(cache, project_id)
    return user


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current user's password",
    responses=USER_RESPONSES,
)
async def change_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, service: UserServiceDep
) -> None:
    await service.change_password(current_user, payload)
