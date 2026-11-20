from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, Field

from app.core.constants import PASSWORD_MAX_BYTES, PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.core.messages import DUE_DATE_MUST_BE_FUTURE_MESSAGE, PASSWORD_TOO_LONG_MESSAGE


def _fits_bcrypt(value: str) -> str:
    if len(value.encode()) > PASSWORD_MAX_BYTES:
        raise ValueError(PASSWORD_TOO_LONG_MESSAGE.format(max_bytes=PASSWORD_MAX_BYTES))
    return value


Password = Annotated[
    str,
    Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH),
    AfterValidator(_fits_bcrypt),
]


def _must_be_future(value: datetime) -> datetime:
    if value <= datetime.now(UTC):
        raise ValueError(DUE_DATE_MUST_BE_FUTURE_MESSAGE)
    return value


FutureDatetime = Annotated[AwareDatetime, AfterValidator(_must_be_future)]
