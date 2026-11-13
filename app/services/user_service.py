from app.core.exceptions import BadRequestError
from app.core.messages import WRONG_PASSWORD_MESSAGE
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import ChangePasswordRequest, UserUpdate


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def update_profile(self, user: User, payload: UserUpdate) -> User:
        return await self._users.update(user, payload.model_dump(exclude_unset=True))

    async def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if not await verify_password(payload.current_password, user.hashed_password):
            raise BadRequestError(WRONG_PASSWORD_MESSAGE)
        hashed_password = await hash_password(payload.new_password)
        await self._users.update(user, {"hashed_password": hashed_password})
