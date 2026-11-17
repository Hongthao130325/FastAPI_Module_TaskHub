from datetime import datetime

from pydantic import EmailStr, Field

from app.core.constants import (
    USER_EMAIL_MAX_LENGTH,
    USER_FULL_NAME_MAX_LENGTH,
    USER_PASSWORD_MAX_LENGTH,
    USER_PASSWORD_MIN_LENGTH,
)
from app.models.enums import UserRole
from app.schemas.base import BaseSchema


class UserRegister(BaseSchema):
    email: EmailStr = Field(max_length=USER_EMAIL_MAX_LENGTH)
    full_name: str = Field(min_length=1, max_length=USER_FULL_NAME_MAX_LENGTH)
    password: str = Field(
        min_length=USER_PASSWORD_MIN_LENGTH,
        max_length=USER_PASSWORD_MAX_LENGTH,
    )


class UserRead(BaseSchema):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserLogin(BaseSchema):
    email: EmailStr = Field(max_length=USER_EMAIL_MAX_LENGTH)
    password: str = Field(
        min_length=USER_PASSWORD_MIN_LENGTH,
        max_length=USER_PASSWORD_MAX_LENGTH,
    )


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseSchema):
    refresh_token: str = Field(min_length=1)


class ChangePassword(BaseSchema):
    current_password: str = Field(
        min_length=USER_PASSWORD_MIN_LENGTH,
        max_length=USER_PASSWORD_MAX_LENGTH,
    )
    new_password: str = Field(
        min_length=USER_PASSWORD_MIN_LENGTH,
        max_length=USER_PASSWORD_MAX_LENGTH,
    )
