from enum import StrEnum
from typing import ClassVar

from app.core.messages import NOT_FOUND_MESSAGE


class ErrorCode(StrEnum):
    APPLICATION_ERROR = "application_error"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    AUTHENTICATION = "authentication_error"
    BAD_REQUEST = "bad_request"
    UNPROCESSABLE_ENTITY = "unprocessable_entity"
    FORBIDDEN = "forbidden"


class AppException(Exception):
    status_code: ClassVar[int] = 500
    code: ClassVar[str] = ErrorCode.APPLICATION_ERROR


class NotFoundError(AppException):
    status_code = 404
    code = ErrorCode.NOT_FOUND

    def __init__(self, resource: str, resource_id: int | str) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(NOT_FOUND_MESSAGE.format(resource=resource, resource_id=resource_id))


class ConflictError(AppException):
    status_code = 409
    code = ErrorCode.CONFLICT
    """Data conflicts with an existing resource."""


class AuthenticationError(AppException):
    status_code = 401
    code = ErrorCode.AUTHENTICATION
    """Authentication failed or a token is invalid."""


class BadRequestError(AppException):
    status_code = 400
    code = ErrorCode.BAD_REQUEST
    """The request is invalid from a business perspective."""


class UnprocessableEntityError(AppException):
    status_code = 422
    code = ErrorCode.UNPROCESSABLE_ENTITY
    """The request is well-formed but violates domain validation."""


class ForbiddenError(AppException):
    status_code = 403
    code = ErrorCode.FORBIDDEN
    """The authenticated user lacks permission."""
