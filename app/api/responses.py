from typing import Any

AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Authentication is required or the token is invalid"},
    422: {"description": "The request payload is invalid"},
}
