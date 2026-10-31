from app.core.exceptions import NotFoundError
from app.models.workspace import Workspace
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    def __init__(self, repo: WorkspaceRepository) -> None:
        self._repo = repo

    async def create(self, payload: WorkspaceCreate, owner_id: int) -> Workspace:
        return await self._repo.create(name=payload.name, owner_id=owner_id)

    async def get(self, workspace_id: int) -> Workspace:
        workspace = await self._repo.get(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", workspace_id)
        return workspace

    async def get_all(self) -> list[Workspace]:
        return await self._repo.get_all()

    async def update(self, workspace_id: int, payload: WorkspaceUpdate) -> Workspace:
        workspace = await self.get(workspace_id)
        data = payload.model_dump(exclude_unset=True)
        return await self._repo.update(workspace, data)

    async def delete(self, workspace_id: int) -> None:
        await self.get(workspace_id)  # ném NotFoundError nếu không tồn tại
        await self._repo.delete(workspace_id)