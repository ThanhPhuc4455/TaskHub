import re

from pydantic import ConfigDict, Field, field_validator

from app.core.constants import (
    COLOR_MAX_LENGTH,
    INVALID_COLOR_MESSAGE,
    LABEL_NAME_MAX_LENGTH,
    LABEL_NAME_MIN_LENGTH,
)
from app.schemas.base import BasePatchSchema, BaseSchema


class LabelCreate(BaseSchema):
    name: str = Field(min_length=LABEL_NAME_MIN_LENGTH, max_length=LABEL_NAME_MAX_LENGTH)
    color: str = Field(default="#808080", min_length=COLOR_MAX_LENGTH, max_length=COLOR_MAX_LENGTH)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
            raise ValueError(INVALID_COLOR_MESSAGE)
        return value.upper()


class LabelUpdate(BasePatchSchema):
    name: str | None = Field(
        default=None, min_length=LABEL_NAME_MIN_LENGTH, max_length=LABEL_NAME_MAX_LENGTH
    )
    color: str | None = Field(
        default=None, min_length=COLOR_MAX_LENGTH, max_length=COLOR_MAX_LENGTH
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
            raise ValueError(INVALID_COLOR_MESSAGE)
        return value.upper() if value is not None else None


class LabelRead(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str
