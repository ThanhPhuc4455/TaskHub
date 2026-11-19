from typing import cast

from fastapi import APIRouter

from app.api.deps import AdminUser, PaginationDep, WorkspaceServiceDep
from app.api.responses import RBAC_RESPONSES
from app.schemas.page import PageResponse
from app.schemas.workspace import WorkspaceRead

router = APIRouter(prefix="/admin", tags=["admin"], responses=RBAC_RESPONSES)


@router.get(
    "/workspaces", response_model=PageResponse[WorkspaceRead], summary="List all workspaces"
)
async def list_all_workspaces(
    _: AdminUser,
    service: WorkspaceServiceDep,
    pagination: PaginationDep,
) -> PageResponse[WorkspaceRead]:
    result = await service.list_all(pagination)
    return PageResponse.from_result(
        cast(list[WorkspaceRead], result.items),
        result.total,
        pagination.page,
        pagination.limit,
    )
