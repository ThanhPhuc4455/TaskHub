from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.database import get_db_session
from app.core.exceptions import ForbiddenError
from app.core.messages import FORBIDDEN_MESSAGE
from app.core.pagination import Pagination
from app.core.security import TokenType, decode_token
from app.models.enums import WorkspaceMemberRole
from app.models.user import User, UserRole
from app.models.workspace import Workspace
from app.repositories.project_repository import ProjectRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.member_service import MemberService
from app.services.project_service import ProjectAccessContext, ProjectService
from app.services.user_context import resolve_user
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService


def get_workspace_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRepository:
    return WorkspaceRepository(session)


def get_pagination(
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> Pagination:
    return Pagination(page=page, limit=limit)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


def get_workspace_member_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceMemberRepository:
    return WorkspaceMemberRepository(session)


def get_workspace_service(
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
    members: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repository)],
) -> WorkspaceService:
    return WorkspaceService(workspaces, members)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_project_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectRepository:
    return ProjectRepository(session)


def get_project_service(
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    workspaces: WorkspaceServiceDep,
) -> ProjectService:
    return ProjectService(projects, workspaces)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    return UserRepository(session)


def get_member_service(
    workspaces: Annotated[WorkspaceService, Depends(get_workspace_service)],
    members: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> MemberService:
    return MemberService(workspaces, members, users)


MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def get_auth_service(
    users: UserRepositoryDep,
    tokens: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> AuthService:
    return AuthService(users, tokens)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    users: UserRepositoryDep,
) -> User:
    payload = decode_token(token, TokenType.ACCESS)
    return await resolve_user(payload.user_id, users)


def get_user_service(
    users: UserRepositoryDep,
    tokens: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> UserService:
    return UserService(users, tokens)


CurrentUser = Annotated[User, Depends(get_current_user)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError(FORBIDDEN_MESSAGE)
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


def require_workspace_role(
    required: WorkspaceMemberRole,
) -> Callable[..., Awaitable[Workspace]]:
    async def dependency(
        workspace_id: int,
        current_user: CurrentUser,
        service: WorkspaceServiceDep,
    ) -> Workspace:
        return await service.require_role(workspace_id, current_user, required)

    return dependency


WorkspaceViewer = Annotated[
    Workspace,
    Depends(require_workspace_role(WorkspaceMemberRole.VIEWER)),
]
WorkspaceOwner = Annotated[
    Workspace,
    Depends(require_workspace_role(WorkspaceMemberRole.OWNER)),
]


def require_project_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    async def dependency(
        project_id: int,
        projects: ProjectServiceDep,
        current_user: CurrentUser,
    ) -> ProjectAccessContext:
        return await projects.require_project_role(project_id, current_user, required)

    return dependency
