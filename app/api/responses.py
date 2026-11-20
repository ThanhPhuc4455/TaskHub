from typing import Any

AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required or the token is invalid"},
    422: {"description": "The request payload is invalid"},
}

RBAC_RESPONSES: dict[int | str, dict[str, Any]] = {
    **AUTH_RESPONSES,
    403: {"description": "The authenticated user lacks permission"},
    404: {"description": "The resource was not found or is not visible"},
    409: {"description": "The request conflicts with an existing resource"},
}
