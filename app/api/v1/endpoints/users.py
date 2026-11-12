from fastapi import APIRouter, status

from app.api.deps import CurrentUser, UserServiceDep
from app.api.responses import AUTH_RESPONSES
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], responses=AUTH_RESPONSES)


@router.get("/me", response_model=UserRead, summary="Get the current user profile")
async def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserRead, summary="Update the current user profile")
async def update_me(
    payload: UserUpdate, current_user: CurrentUser, service: UserServiceDep
) -> User:
    return await service.update_profile(current_user, payload)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current user's password",
    responses={400: {"description": "The current password is incorrect"}},
)
async def change_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, service: UserServiceDep
) -> None:
    await service.change_password(current_user, payload)
