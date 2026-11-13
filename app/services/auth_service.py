from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.messages import (
    EMAIL_TAKEN_MESSAGE,
    INACTIVE_USER_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    INVALID_TOKEN_MESSAGE,
)
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services.user_context import resolve_user


class AuthService:
    def __init__(self, users: UserRepository, tokens: RefreshTokenRepository) -> None:
        self._users = users
        self._tokens = tokens

    async def register(self, payload: RegisterRequest) -> User:
        hashed_password = await hash_password(payload.password)
        try:
            return await self._users.create(
                email=payload.email,
                full_name=payload.full_name,
                hashed_password=hashed_password,
            )
        except IntegrityError as exc:
            await self._users.rollback()
            raise ConflictError(EMAIL_TAKEN_MESSAGE) from exc

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._users.get_by_email(email.lower())
        if user is None or not await verify_password(password, user.hashed_password):
            raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)
        if not user.is_active:
            raise AuthenticationError(INACTIVE_USER_MESSAGE)
        return await self._issue_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, TokenType.REFRESH)
        stored = await self._tokens.get_by_jti(payload.jti)
        if stored is None:
            raise AuthenticationError(INVALID_TOKEN_MESSAGE)
        if stored.revoked:
            await self._tokens.revoke_all_for_user(payload.user_id)
            raise AuthenticationError(INVALID_TOKEN_MESSAGE)
        if not await self._tokens.claim_for_rotation(payload.jti, commit=False):
            await self._tokens.revoke_all_for_user(payload.user_id)
            raise AuthenticationError(INVALID_TOKEN_MESSAGE)
        user = await resolve_user(payload.user_id, self._users)
        tokens = await self._issue_tokens(user.id, commit=False)
        await self._tokens.commit()
        return tokens

    async def logout(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token, TokenType.REFRESH)
        stored = await self._tokens.get_by_jti(payload.jti)
        if stored is None:
            raise AuthenticationError(INVALID_TOKEN_MESSAGE)
        if not stored.revoked:
            await self._tokens.claim_for_rotation(payload.jti)

    async def _issue_tokens(self, user_id: int, *, commit: bool = True) -> TokenResponse:
        access = create_access_token(user_id)
        refresh = create_refresh_token(user_id)
        await self._tokens.create(
            commit=commit,
            jti=refresh.jti,
            user_id=user_id,
            expires_at=refresh.expires_at,
        )
        return TokenResponse(access_token=access.token, refresh_token=refresh.token)
