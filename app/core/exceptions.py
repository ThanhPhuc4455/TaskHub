from app.core.messages import NOT_FOUND_MESSAGE


class AppException(Exception):
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)


class NotFoundError(AppException):
    status_code = 404

    def __init__(self, resource: str, resource_id: int | str) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(NOT_FOUND_MESSAGE.format(resource=resource, resource_id=resource_id))


class ConflictError(AppException):
    status_code = 409
    """Data conflicts with an existing resource."""


class AuthenticationError(AppException):
    status_code = 401
    """Authentication failed or a token is invalid."""


class BadRequestError(AppException):
    status_code = 400
    """The request is invalid from a business perspective."""


class ForbiddenError(AppException):
    status_code = 403
    """The authenticated user lacks permission."""
