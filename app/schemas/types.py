from typing import Annotated

from pydantic import AfterValidator, Field

from app.core.constants import PASSWORD_MAX_BYTES, PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.core.messages import PASSWORD_TOO_LONG_MESSAGE


def _fits_bcrypt(value: str) -> str:
    if len(value.encode()) > PASSWORD_MAX_BYTES:
        raise ValueError(PASSWORD_TOO_LONG_MESSAGE.format(max_bytes=PASSWORD_MAX_BYTES))
    return value


Password = Annotated[
    str,
    Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH),
    AfterValidator(_fits_bcrypt),
]
