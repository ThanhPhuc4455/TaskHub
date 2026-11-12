from typing import Any

RBAC_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required or the token is invalid"},
    403: {"description": "The authenticated user lacks permission"},
    404: {"description": "The resource was not found or is not visible"},
    409: {"description": "The request conflicts with an existing resource"},
    422: {"description": "The request payload or query parameters are invalid"},
}
