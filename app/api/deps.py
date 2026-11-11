from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import FORBIDDEN_MESSAGE, INVALID_TOKEN_MESSAGE
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.pagination import Pagination
from app.core.security import ACCESS, decode_token
from app.models.enums import WorkspaceMemberRole
from app.models.user import User, UserRole
from app.repositories.project_repository import ProjectRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.member_service import MemberService
from app.services.project_service import ProjectAccessContext, ProjectService
from app.services.user_service import UserService
from app.services.workspace_service import (
    WorkspaceAccessContext,
    WorkspaceService,
    authorize_resource,
)


def get_workspace_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRepository:
    return WorkspaceRepository(session)


def get_pagination(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=100),
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


def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    tokens: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
) -> AuthService:
    return AuthService(users, tokens)


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


def require_workspace_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    async def dependency(
        workspace_id: int,
        service: WorkspaceServiceDep,
        current_user: CurrentUser,
    ) -> WorkspaceAccessContext:
        return await service.authorize(workspace_id, current_user, required)

    return dependency


def require_project_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    async def dependency(
        project_id: int,
        projects: Annotated[ProjectRepository, Depends(get_project_repository)],
        workspaces: WorkspaceServiceDep,
        current_user: CurrentUser,
    ) -> ProjectAccessContext:
        project = await projects.get(project_id)
        project, workspace = await authorize_resource(
            project,
            "Project",
            project.workspace_id if project is not None else project_id,
            current_user,
            required,
            workspaces,
        )
        assert project is not None
        return ProjectAccessContext(project=project, workspace=workspace)

    return dependency
