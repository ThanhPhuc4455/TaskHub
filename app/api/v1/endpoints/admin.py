from fastapi import APIRouter

from app.api.deps import AdminUser, PaginationDep, WorkspaceServiceDep
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/workspaces", response_model=list[WorkspaceRead], summary="List all workspaces")
async def list_all_workspaces(
    _: AdminUser,
    service: WorkspaceServiceDep,
    pagination: PaginationDep,
) -> list[Workspace]:
    return await service.list_all(pagination)
