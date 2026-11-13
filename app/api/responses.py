from typing import Any

from app.schemas.error import ErrorResponse

ERROR_RESPONSE_CONTENT: dict[str, Any] = {"model": ErrorResponse}

RBAC_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "Authentication is required or the token is invalid",
        **ERROR_RESPONSE_CONTENT,
    },
    403: {
        "description": "The authenticated user lacks permission",
        **ERROR_RESPONSE_CONTENT,
    },
    404: {
        "description": "The resource was not found or is not visible",
        **ERROR_RESPONSE_CONTENT,
    },
    409: {
        "description": "The request conflicts with an existing resource",
        **ERROR_RESPONSE_CONTENT,
    },
    422: {
        "description": "The request payload or query parameters are invalid",
        **ERROR_RESPONSE_CONTENT,
    },
    500: {
        "description": "An unexpected server error occurred",
        **ERROR_RESPONSE_CONTENT,
    },
}

PUBLIC_REGISTER_RESPONSES: dict[int | str, dict[str, Any]] = {
    409: {"description": "The email is already registered", **ERROR_RESPONSE_CONTENT},
    422: {"description": "The request payload is invalid", **ERROR_RESPONSE_CONTENT},
    500: {"description": "An unexpected server error occurred", **ERROR_RESPONSE_CONTENT},
}

AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication failed or the token is invalid", **ERROR_RESPONSE_CONTENT},
    409: {
        "description": "The request conflicts with an existing resource",
        **ERROR_RESPONSE_CONTENT,
    },
    422: {"description": "The request payload is invalid", **ERROR_RESPONSE_CONTENT},
    500: {"description": "An unexpected server error occurred", **ERROR_RESPONSE_CONTENT},
}

USER_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"description": "The request is invalid", **ERROR_RESPONSE_CONTENT},
    401: {
        "description": "Authentication is required or the token is invalid",
        **ERROR_RESPONSE_CONTENT,
    },
    422: {"description": "The request payload is invalid", **ERROR_RESPONSE_CONTENT},
    500: {"description": "An unexpected server error occurred", **ERROR_RESPONSE_CONTENT},
}

SYSTEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    500: {"description": "An unexpected server error occurred", **ERROR_RESPONSE_CONTENT},
}
