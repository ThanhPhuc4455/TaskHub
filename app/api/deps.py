from collections.abc import AsyncIterator, Callable
from typing import Annotated, Any

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheBackend, RedisCacheBackend
from app.core.config import settings
from app.core.constants import (
    DEFAULT_PAGE_SIZE,
    FORBIDDEN_MESSAGE,
    INVALID_TOKEN_MESSAGE,
    MAX_PAGE_SIZE,
)
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError, ForbiddenError, NotFoundError
from app.core.pagination import Pagination
from app.core.security import ACCESS, decode_token
from app.models.enums import WorkspaceMemberRole
from app.models.user import User, UserRole
from app.repositories.comment_repository import CommentRepository
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.comment_service import CommentAccessContext, CommentService
from app.services.label_service import LabelAccessContext, LabelService
from app.services.member_service import MemberService
from app.services.project_service import ProjectAccessContext, ProjectService
from app.services.task_service import TaskAccessContext, TaskService
from app.services.user_service import UserService
from app.services.workspace_service import (
    WorkspaceAccessContext,
    WorkspaceService,
)


async def get_cache_backend() -> AsyncIterator[CacheBackend]:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    backend = RedisCacheBackend(client)
    try:
        yield backend
    finally:
        await backend.close()


CacheDep = Annotated[CacheBackend, Depends(get_cache_backend)]


def get_workspace_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WorkspaceRepository:
    return WorkspaceRepository(session)


def get_pagination(
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
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


def get_task_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskRepository:
    return TaskRepository(session)


def get_label_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LabelRepository:
    return LabelRepository(session)


def get_comment_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CommentRepository:
    return CommentRepository(session)


def get_task_service(
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    members: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repository)],
) -> TaskService:
    return TaskService(tasks, projects, members)


def get_label_service(
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
) -> LabelService:
    return LabelService(labels, tasks)


def get_comment_service(
    comments: Annotated[CommentRepository, Depends(get_comment_repository)],
) -> CommentService:
    return CommentService(comments)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


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
        service: ProjectServiceDep,
        current_user: CurrentUser,
    ) -> ProjectAccessContext:
        return await service.require_project_role(project_id, current_user, required)

    return dependency


async def _resolve_project_access(
    project: Any,
    resource_name: str,
    resource_id: int,
    required: WorkspaceMemberRole,
    current_user: User,
    workspaces: WorkspaceService,
) -> ProjectAccessContext:
    if project is None:
        raise NotFoundError(resource_name, resource_id)
    workspace = await workspaces.authorize(project.workspace_id, current_user, required)
    return ProjectAccessContext(project=project, workspace=workspace)


def require_task_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    async def dependency(
        task_id: int,
        tasks: Annotated[TaskRepository, Depends(get_task_repository)],
        projects: Annotated[ProjectRepository, Depends(get_project_repository)],
        workspaces: WorkspaceServiceDep,
        current_user: CurrentUser,
    ) -> TaskAccessContext:
        task = await tasks.get_with_details(task_id)
        if task is None:
            raise NotFoundError("Task", task_id)
        project = await projects.get(task.project_id)
        project_access = await _resolve_project_access(
            project, "Project", task.project_id, required, current_user, workspaces
        )
        return TaskAccessContext(
            task=task,
            project=project_access.project,
            workspace=project_access.workspace,
        )

    return dependency


def require_label_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    async def dependency(
        label_id: int,
        labels: Annotated[LabelRepository, Depends(get_label_repository)],
        projects: Annotated[ProjectRepository, Depends(get_project_repository)],
        workspaces: WorkspaceServiceDep,
        current_user: CurrentUser,
    ) -> LabelAccessContext:
        label = await labels.get(label_id)
        if label is None:
            raise NotFoundError("Label", label_id)
        project = await projects.get(label.project_id)
        project_access = await _resolve_project_access(
            project, "Project", label.project_id, required, current_user, workspaces
        )
        return LabelAccessContext(
            label=label,
            project=project_access.project,
            workspace=project_access.workspace,
        )

    return dependency


def require_comment_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    async def dependency(
        task_id: int,
        comment_id: int,
        comments: Annotated[CommentRepository, Depends(get_comment_repository)],
        tasks: Annotated[TaskRepository, Depends(get_task_repository)],
        projects: Annotated[ProjectRepository, Depends(get_project_repository)],
        workspaces: WorkspaceServiceDep,
        current_user: CurrentUser,
    ) -> CommentAccessContext:
        comment = await comments.get_with_author(comment_id)
        if comment is None or comment.task_id != task_id:
            raise NotFoundError("Comment", comment_id)
        task = await tasks.get_with_details(comment.task_id)
        if task is None:
            raise NotFoundError("Task", comment.task_id)
        project = await projects.get(task.project_id)
        project_access = await _resolve_project_access(
            project, "Project", task.project_id, required, current_user, workspaces
        )
        return CommentAccessContext(
            comment=comment,
            task=TaskAccessContext(
                task=task,
                project=project_access.project,
                workspace=project_access.workspace,
            ),
        )

    return dependency
