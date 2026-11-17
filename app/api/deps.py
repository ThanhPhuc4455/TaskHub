from collections.abc import Awaitable, Callable
from typing import Annotated, Any, cast

from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheBackend, RedisCacheBackend
from app.core.config import settings
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.database import get_db_session
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.messages import FORBIDDEN_MESSAGE
from app.core.pagination import Pagination
from app.core.security import TokenType, decode_token
from app.models.comment import Comment
from app.models.enums import WorkspaceMemberRole
from app.models.label import Label
from app.models.task import Task
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
) -> UserService:
    return UserService(users, tokens)


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


def require_project_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    async def dependency(
        project_id: int, projects: ProjectServiceDep, current_user: CurrentUser
    ) -> ProjectAccessContext:
        return await projects.require_project_role(project_id, current_user, required)

    return dependency


def require_project_resource_role(
    required: WorkspaceMemberRole, resource: str
) -> Callable[..., Any]:
    async def dependency(
        comments: Annotated[CommentRepository, Depends(get_comment_repository)],
        tasks: Annotated[TaskRepository, Depends(get_task_repository)],
        labels: Annotated[LabelRepository, Depends(get_label_repository)],
        projects: ProjectServiceDep,
        current_user: CurrentUser,
        members: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repository)],
        task_id: int | None = None,
        label_id: int | None = None,
        comment_id: int | None = None,
    ) -> TaskAccessContext | LabelAccessContext | CommentAccessContext:
        if resource == "task":
            if task_id is None:
                raise NotFoundError("Task", "missing")
            task = await tasks.get_with_details(task_id)
            if task is None:
                raise NotFoundError("Task", task_id)
            access = await projects.require_project_role(task.project_id, current_user, required)
        elif resource == "label":
            if label_id is None:
                raise NotFoundError("Label", "missing")
            label = await labels.get(label_id)
            if label is None:
                raise NotFoundError("Label", label_id)
            access = await projects.require_project_role(label.project_id, current_user, required)
        elif resource == "comment":
            if task_id is None or comment_id is None:
                raise NotFoundError("Comment", comment_id or "missing")
            comment = await comments.get_with_author(comment_id)
            if comment is None or comment.task_id != task_id:
                raise NotFoundError("Comment", comment_id)
            task = await tasks.get_with_details(task_id)
            if task is None:
                raise NotFoundError("Task", task_id)
            access = await projects.require_project_role(task.project_id, current_user, required)
        else:
            raise NotFoundError("Resource", resource)

        if current_user.role == UserRole.ADMIN:
            role = WorkspaceMemberRole.OWNER
        else:
            membership = await members.get_membership(access.workspace.id, current_user.id)
            if membership is None:
                raise NotFoundError("Workspace", access.workspace.id)
            role = membership.role

        if resource == "task":
            return TaskAccessContext(
                task=cast(Task, task),
                project=access.project,
                workspace=access.workspace,
                effective_role=role,
            )
        if resource == "label":
            return LabelAccessContext(
                label=cast(Label, label),
                project=access.project,
                workspace=access.workspace,
                effective_role=role,
            )
        return CommentAccessContext(
            comment=cast(Comment, comment),
            task=TaskAccessContext(
                task=cast(Task, task),
                project=access.project,
                workspace=access.workspace,
                effective_role=role,
            ),
        )

    return dependency


def require_task_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    return require_project_resource_role(required, "task")


def require_label_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    return require_project_resource_role(required, "label")


def require_comment_role(required: WorkspaceMemberRole) -> Callable[..., Any]:
    return require_project_resource_role(required, "comment")
