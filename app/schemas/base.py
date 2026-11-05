from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator


class BaseSchema(BaseModel):
    """Schema nhận dữ liệu từ client: tự cắt khoảng trắng hai đầu chuỗi."""

    model_config = ConfigDict(str_strip_whitespace=True)


class BasePatchSchema(BaseSchema):
    """Schema cho PATCH: field bắt buộc không được gửi null tường minh."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def reject_explicit_null(self) -> Self:
        for field in self.model_fields_set:
            if field not in self.nullable_fields and getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self
