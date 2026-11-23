from pydantic import BaseModel


class PageResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    limit: int

    @classmethod
    def from_result(cls, items: list[T], total: int, page: int, limit: int) -> "PageResponse[T]":
        return cls(items=items, total=total, page=page, limit=limit)
