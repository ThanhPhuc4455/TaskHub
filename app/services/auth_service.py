from app.core.exceptions import AuthenticationError, ConflictError
from app.core.messages import (
    EMAIL_TAKEN_MESSAGE,
    INACTIVE_USER_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    INVALID_TOKEN_MESSAGE,
)
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def register(self, payload: RegisterRequest) -> User:
        if await self._users.get_by_email(payload.email) is not None:
            raise ConflictError(EMAIL_TAKEN_MESSAGE)
        hashed_password = await hash_password(payload.password)
        return await self._users.create(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hashed_password,
        )

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._users.get_by_email(email.lower())
        if user is None or not await verify_password(password, user.hashed_password):
            raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)
        if not user.is_active:
            raise AuthenticationError(INACTIVE_USER_MESSAGE)
        return self._issue_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, REFRESH)
        user = await self._users.get(payload.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError(INVALID_TOKEN_MESSAGE)
        return self._issue_tokens(user.id)

    @staticmethod
    def _issue_tokens(user_id: int) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user_id).token,
            refresh_token=create_refresh_token(user_id).token,
        )
