from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints, field_validator

from app.core.constants import EMAIL_MAX_LENGTH, FULL_NAME_MAX_LENGTH, FULL_NAME_MIN_LENGTH
from app.schemas.types import Password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Password
    full_name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=FULL_NAME_MIN_LENGTH,
            max_length=FULL_NAME_MAX_LENGTH,
        ),
    ]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        if len(value) > EMAIL_MAX_LENGTH:
            raise ValueError(f"email must be at most {EMAIL_MAX_LENGTH} characters")
        return value.lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
