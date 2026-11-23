from datetime import datetime

from pydantic import ConfigDict, Field, PositiveInt

from app.core.constants import COMMENT_CONTENT_MAX_LENGTH, MAX_PAGE_SIZE
from app.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=COMMENT_CONTENT_MAX_LENGTH)


class CommentUpdate(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=COMMENT_CONTENT_MAX_LENGTH)


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
