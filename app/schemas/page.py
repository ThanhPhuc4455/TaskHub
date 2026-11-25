from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.core.pagination import PageResult, Pagination


class PageResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    limit: int

    @classmethod
    def from_result(cls, items: list[T], total: int, page: int, limit: int) -> "PageResponse[T]":
        return cls(items=items, total=total, page=page, limit=limit)

    @classmethod
    def from_page_result(
        cls, result: "PageResult[Any]", pagination: "Pagination"
    ) -> "PageResponse[T]":
        return cls(
            items=result.items,
            total=result.total,
            page=pagination.page,
            limit=pagination.limit,
        )
