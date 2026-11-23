from datetime import datetime

from pydantic import ConfigDict, Field, PositiveInt, field_validator

from app.core.constants import MAX_PAGE_SIZE
from app.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)


class CommentUpdate(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)

    @field_validator("content", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("Field cannot be null.")

        return value


class CommentResponse(BaseSchema):
    id: PositiveInt
    task_id: PositiveInt
    author_id: PositiveInt
    content: str
    created_at: datetime


class CommentListResponse(BaseSchema):
    items: list[CommentResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=MAX_PAGE_SIZE)
