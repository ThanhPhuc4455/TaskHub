from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.repositories.workspace_repository import WorkspaceRepository
from app.services.workspace_service import WorkspaceService


@lru_cache
def get_workspace_repository() -> WorkspaceRepository:
    return WorkspaceRepository()


def get_workspace_service(
    repo: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> WorkspaceService:
    return WorkspaceService(repo)


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
