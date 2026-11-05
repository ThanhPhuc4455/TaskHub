from fastapi import APIRouter, status

from app.api.deps import CurrentUser, UserServiceDep
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate, current_user: CurrentUser, service: UserServiceDep
) -> User:
    return await service.update_profile(current_user, payload)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, service: UserServiceDep
) -> None:
    await service.change_password(current_user, payload)
