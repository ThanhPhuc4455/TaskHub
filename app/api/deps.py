from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheBackend, RedisCacheBackend, TaskCacheInvalidator
from app.core.config import settings
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.database import get_db_session
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.messages import FORBIDDEN_MESSAGE
from app.core.pagination import Pagination
from app.core.security import TokenType, decode_token
from app.models.enums import WorkspaceMemberRole
from app.models.user import User, UserRole
from app.models.workspace import Workspace
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
from app.services.notification_service import LoggingNotificationService, NotificationService
from app.services.project_service import ProjectAccessContext, ProjectService
from app.services.task_service import TaskAccessContext, TaskService
from app.services.user_context import resolve_user
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService


def get_notification_service() -> NotificationService:
    return LoggingNotificationService()


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


def get_cache_backend(request: Request) -> CacheBackend:
    return RedisCacheBackend(request.app.state.redis_client)


CacheDep = Annotated[CacheBackend, Depends(get_cache_backend)]


def get_task_cache_invalidator(cache: CacheDep) -> TaskCacheInvalidator:
    return TaskCacheInvalidator(cache)


TaskCacheInvalidatorDep = Annotated[TaskCacheInvalidator, Depends(get_task_cache_invalidator)]


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
    cache: CacheDep,
    invalidator: TaskCacheInvalidatorDep,
) -> WorkspaceService:
    return WorkspaceService(workspaces, members, invalidator)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_project_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectRepository:
    return ProjectRepository(session)


def get_project_service(
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    workspaces: WorkspaceServiceDep,
    invalidator: TaskCacheInvalidatorDep,
) -> ProjectService:
    return ProjectService(projects, workspaces, invalidator)


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
    cache: CacheDep,
    invalidator: TaskCacheInvalidatorDep,
) -> TaskService:
    return TaskService(tasks, projects, members, cache, invalidator)


def get_label_service(
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    invalidator: TaskCacheInvalidatorDep,
) -> LabelService:
    return LabelService(labels, tasks, invalidator)


def get_comment_service(
    comments: Annotated[CommentRepository, Depends(get_comment_repository)],
    invalidator: TaskCacheInvalidatorDep,
) -> CommentService:
    return CommentService(comments, invalidator)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    return UserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_member_service(
    workspaces: WorkspaceServiceDep,
    members: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repository)],
    users: UserRepositoryDep,
) -> MemberService:
    return MemberService(workspaces, members, users)


MemberServiceDep = Annotated[MemberService, Depends(get_member_service)]


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
    token: Annotated[str, Depends(oauth2_scheme)], users: UserRepositoryDep
) -> User:
    payload = decode_token(token, TokenType.ACCESS)
    return await resolve_user(payload.user_id, users)


def get_user_service(
    users: UserRepositoryDep,
    tokens: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    invalidator: TaskCacheInvalidatorDep,
) -> UserService:
    return UserService(users, tokens, tasks, invalidator)


CurrentUser = Annotated[User, Depends(get_current_user)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError(FORBIDDEN_MESSAGE)
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


def require_workspace_role(required: WorkspaceMemberRole) -> Callable[..., Awaitable[Workspace]]:
    async def dependency(
        workspace_id: int, current_user: CurrentUser, service: WorkspaceServiceDep
    ) -> Workspace:
        return await service.require_role(workspace_id, current_user, required)

    return dependency


WorkspaceViewer = Annotated[Workspace, Depends(require_workspace_role(WorkspaceMemberRole.VIEWER))]
WorkspaceOwner = Annotated[Workspace, Depends(require_workspace_role(WorkspaceMemberRole.OWNER))]


def require_project_role(
    required: WorkspaceMemberRole,
) -> Callable[..., Awaitable[ProjectAccessContext]]:
    async def dependency(
        project_id: int, projects: ProjectServiceDep, current_user: CurrentUser
    ) -> ProjectAccessContext:
        return await projects.require_project_role(project_id, current_user, required)

    return dependency


@dataclass(frozen=True)
class ResourceDependencies:
    comments: CommentRepository
    tasks: TaskRepository
    labels: LabelRepository
    projects: ProjectService
    task_id: int | None
    label_id: int | None
    comment_id: int | None


async def _load_task_context(
    resources: ResourceDependencies, user: User, required: WorkspaceMemberRole
) -> TaskAccessContext:
    if resources.task_id is None:
        raise NotFoundError("Task", "missing")
    task = await resources.tasks.get_with_details(resources.task_id)
    if task is None:
        raise NotFoundError("Task", resources.task_id)
    access = await resources.projects.require_project_role(task.project_id, user, required)
    return TaskAccessContext(
        task=task,
        project=access.project,
        workspace=access.workspace,
        effective_role=access.effective_role,
    )


async def _load_label_context(
    resources: ResourceDependencies, user: User, required: WorkspaceMemberRole
) -> LabelAccessContext:
    if resources.label_id is None:
        raise NotFoundError("Label", "missing")
    label = await resources.labels.get(resources.label_id)
    if label is None:
        raise NotFoundError("Label", resources.label_id)
    access = await resources.projects.require_project_role(label.project_id, user, required)
    return LabelAccessContext(
        label=label,
        project=access.project,
        workspace=access.workspace,
        effective_role=access.effective_role,
    )


async def _load_comment_context(
    resources: ResourceDependencies, user: User, required: WorkspaceMemberRole
) -> CommentAccessContext:
    if resources.task_id is None or resources.comment_id is None:
        raise NotFoundError("Comment", resources.comment_id or "missing")
    comment = await resources.comments.get_with_author(resources.comment_id)
    if comment is None or comment.task_id != resources.task_id:
        raise NotFoundError("Comment", resources.comment_id)
    task = await resources.tasks.get_with_details(resources.task_id)
    if task is None:
        raise NotFoundError("Task", resources.task_id)
    access = await resources.projects.require_project_role(task.project_id, user, required)
    return CommentAccessContext(
        comment=comment,
        task=TaskAccessContext(
            task=task,
            project=access.project,
            workspace=access.workspace,
            effective_role=access.effective_role,
        ),
    )


def require_resource_role[ResourceContext](
    required: WorkspaceMemberRole,
    loader: Callable[[ResourceDependencies, User, WorkspaceMemberRole], Awaitable[ResourceContext]],
) -> Callable[..., Awaitable[ResourceContext]]:
    async def dependency(
        comments: Annotated[CommentRepository, Depends(get_comment_repository)],
        tasks: Annotated[TaskRepository, Depends(get_task_repository)],
        labels: Annotated[LabelRepository, Depends(get_label_repository)],
        projects: ProjectServiceDep,
        current_user: CurrentUser,
        task_id: int | None = None,
        label_id: int | None = None,
        comment_id: int | None = None,
    ) -> ResourceContext:
        return await loader(
            ResourceDependencies(
                comments=comments,
                tasks=tasks,
                labels=labels,
                projects=projects,
                task_id=task_id,
                label_id=label_id,
                comment_id=comment_id,
            ),
            current_user,
            required,
        )

    return dependency


def require_task_role(
    required: WorkspaceMemberRole,
) -> Callable[..., Awaitable[TaskAccessContext]]:
    return require_resource_role(required, _load_task_context)


def require_label_role(
    required: WorkspaceMemberRole,
) -> Callable[..., Awaitable[LabelAccessContext]]:
    return require_resource_role(required, _load_label_context)


def require_comment_role(
    required: WorkspaceMemberRole,
) -> Callable[..., Awaitable[CommentAccessContext]]:
    return require_resource_role(required, _load_comment_context)
