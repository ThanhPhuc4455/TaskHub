from datetime import UTC, datetime
from typing import Any

from app.models.workspace import Workspace


class WorkspaceRepository:
    def __init__(self) -> None:
        self._items: dict[int, Workspace] = {}
        self._next_id = 1

    async def create(self, *, name: str, owner_id: int) -> Workspace:
        workspace = Workspace(
            id=self._next_id,
            name=name,
            owner_id=owner_id,
            created_at=datetime.now(UTC),
        )
        self._items[workspace.id] = workspace
        self._next_id += 1
        return workspace

    async def get(self, workspace_id: int) -> Workspace | None:
        return self._items.get(workspace_id)

    async def get_all(self) -> list[Workspace]:
        return list(self._items.values())

    async def update(self, workspace: Workspace, data: dict[str, Any]) -> Workspace:
        for key, value in data.items():
            setattr(workspace, key, value)
        return workspace

    async def delete(self, workspace_id: int) -> None:
        self._items.pop(workspace_id, None)
