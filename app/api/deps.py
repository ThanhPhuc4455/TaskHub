from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import INVALID_TOKEN_MESSAGE
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError
from app.core.security import ACCESS, decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService


def get_workspace_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRepository:
    return WorkspaceRepository(session)


def get_workspace_service(
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> WorkspaceService:
    return WorkspaceService(repo)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    return UserRepository(session)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(users)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    payload = decode_token(token, ACCESS)
    user = await users.get(payload.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError(INVALID_TOKEN_MESSAGE)
    return user


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)


CurrentUser = Annotated[User, Depends(get_current_user)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
