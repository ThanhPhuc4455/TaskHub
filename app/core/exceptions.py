from app.core.constants import NOT_FOUND_MESSAGE


class NotFoundError(Exception):
    def __init__(self, resource: str, resource_id: int) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(NOT_FOUND_MESSAGE.format(resource=resource, resource_id=resource_id))
