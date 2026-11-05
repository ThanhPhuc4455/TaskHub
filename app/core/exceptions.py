from app.core.constants import NOT_FOUND_MESSAGE


class NotFoundError(Exception):
    def __init__(self, resource: str, resource_id: int) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(NOT_FOUND_MESSAGE.format(resource=resource, resource_id=resource_id))


class ConflictError(Exception):
    """Data conflicts with an existing resource."""


class AuthenticationError(Exception):
    """Authentication failed or a token is invalid."""


class BadRequestError(Exception):
    """The request is invalid from a business perspective."""
