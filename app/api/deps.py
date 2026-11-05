from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.repositories.workspace_repository import WorkspaceRepository
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
