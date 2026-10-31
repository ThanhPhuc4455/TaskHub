from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime