from dataclasses import dataclass
from datetime import datetime


@dataclass
class Workspace:
    id: int
    name: str
    owner_id: int
    created_at: datetime