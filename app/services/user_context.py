from app.core.exceptions import AuthenticationError
from app.core.messages import INACTIVE_USER_MESSAGE, INVALID_TOKEN_MESSAGE
from app.models.user import User
from app.repositories.user_repository import UserRepository


async def resolve_user(
    user_id: int,
    users: UserRepository,
    *,
    inactive_message: str = INACTIVE_USER_MESSAGE,
) -> User:
    user = await users.get(user_id)
    if user is None:
        raise AuthenticationError(INVALID_TOKEN_MESSAGE)
    if not user.is_active:
        raise AuthenticationError(inactive_message)
    return user


resolve_active_user = resolve_user
