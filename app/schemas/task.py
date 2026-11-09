from pydantic import Field, field_validator

from app.core.constants import (
    TASK_DESCRIPTION_MAX_LENGTH,
    TASK_TITLE_MAX_LENGTH,
    TASK_TITLE_MIN_LENGTH,
)
from app.core.messages import FIELD_CANNOT_BE_NULL_MESSAGE
from app.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    title: str = Field(
        min_length=TASK_TITLE_MIN_LENGTH,
        max_length=TASK_TITLE_MAX_LENGTH,
    )

    description: str | None = Field(
        default=None,
        max_length=TASK_DESCRIPTION_MAX_LENGTH,
    )


class TaskUpdate(BaseSchema):
    title: str | None = Field(
        default=None,
        min_length=TASK_TITLE_MIN_LENGTH,
        max_length=TASK_TITLE_MAX_LENGTH,
    )

    description: str | None = Field(
        default=None,
        max_length=TASK_DESCRIPTION_MAX_LENGTH,
    )

    is_completed: bool | None = None

    @field_validator("title", "is_completed", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError(FIELD_CANNOT_BE_NULL_MESSAGE)

        return value


class TaskResponse(BaseSchema):
    id: int
    title: str
    description: str | None = None
    is_completed: bool
