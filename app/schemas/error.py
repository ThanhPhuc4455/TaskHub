from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str | list[dict[str, Any]]
    code: str
    request_id: str
