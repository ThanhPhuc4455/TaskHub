from typing import ClassVar

from app.core.constants import APP_ERROR_CODE
from app.core.messages import NOT_FOUND_MESSAGE


class AppException(Exception):
    status_code: ClassVar[int] = 500
    code: ClassVar[str] = APP_ERROR_CODE


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"

    def __init__(self, resource: str, resource_id: int | str) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(NOT_FOUND_MESSAGE.format(resource=resource, resource_id=resource_id))


class ConflictError(AppException):
    status_code = 409
    code = "conflict"
    """Data conflicts with an existing resource."""


class AuthenticationError(AppException):
    status_code = 401
    code = "authentication_error"
    """Authentication failed or a token is invalid."""


class BadRequestError(AppException):
    status_code = 400
    code = "bad_request"
    """The request is invalid from a business perspective."""


class UnprocessableEntityError(AppException):
    status_code = 422
    code = "unprocessable_entity"
    """The request is well-formed but violates domain validation."""


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"
    """The authenticated user lacks permission."""
