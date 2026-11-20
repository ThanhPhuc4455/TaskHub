from dataclasses import dataclass


@dataclass(frozen=True)
class Pagination:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


@dataclass(frozen=True)
class PageResult[T]:
    items: list[T]
    total: int
