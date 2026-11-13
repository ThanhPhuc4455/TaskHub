from fastapi import APIRouter

from app.api.deps import AdminUser, PaginationDep, WorkspaceServiceDep
from app.api.responses import RBAC_RESPONSES
from app.schemas.workspace import WorkspacePageResponse

router = APIRouter(prefix="/admin", tags=["admin"], responses=RBAC_RESPONSES)


@router.get("/workspaces", response_model=WorkspacePageResponse, summary="List all workspaces")
async def list_all_workspaces(
    _: AdminUser,
    service: WorkspaceServiceDep,
    pagination: PaginationDep,
) -> WorkspacePageResponse:
    result = await service.list_all(pagination)
    return WorkspacePageResponse(
        items=result.items, total=result.total, page=pagination.page, limit=pagination.limit
    )
