import asyncio
import enum
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.constants import PASSWORD_MAX_BYTES
from app.core.exceptions import AuthenticationError
from app.core.messages import INVALID_TOKEN_MESSAGE, WRONG_TOKEN_TYPE_MESSAGE


class TokenType(enum.StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    jti: str


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash, password)


async def verify_password(plain: str, hashed: str) -> bool:
    encoded = plain.encode()
    if len(encoded) > PASSWORD_MAX_BYTES:
        return False
    return await asyncio.to_thread(bcrypt.checkpw, encoded, hashed.encode())


def _issue(user_id: int, token_type: str, lifetime: timedelta) -> IssuedToken:
    now = datetime.now(UTC)
    expires_at = now + lifetime
    jti = uuid.uuid4().hex
    token = jwt.encode(
        {"sub": str(user_id), "type": token_type, "iat": now, "exp": expires_at, "jti": jti},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return IssuedToken(token=token, jti=jti, expires_at=expires_at)


def create_access_token(user_id: int) -> IssuedToken:
    return _issue(
        user_id, TokenType.ACCESS, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(user_id: int) -> IssuedToken:
    return _issue(user_id, TokenType.REFRESH, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, expected_type: TokenType) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type", "jti"]},
        )
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError(INVALID_TOKEN_MESSAGE) from exc
    if payload.get("type") != expected_type:
        raise AuthenticationError(WRONG_TOKEN_TYPE_MESSAGE)
    try:
        return TokenPayload(user_id=int(payload["sub"]), jti=str(payload["jti"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError(INVALID_TOKEN_MESSAGE) from exc
