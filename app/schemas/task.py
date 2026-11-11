from datetime import datetime

from pydantic import Field, field_validator

from app.core.constants import (
    MAX_PAGE_SIZE,
    TASK_DESCRIPTION_MAX_LENGTH,
    TASK_TITLE_MAX_LENGTH,
    TASK_TITLE_MIN_LENGTH,
)
from app.core.messages import FIELD_CANNOT_BE_NULL_MESSAGE
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    project_id: int = Field(gt=0)
    created_by: int = Field(gt=0)
    assignee_id: int | None = Field(default=None, gt=0)

    title: str = Field(
        min_length=TASK_TITLE_MIN_LENGTH,
        max_length=TASK_TITLE_MAX_LENGTH,
    )

    description: str | None = Field(
        default=None,
        max_length=TASK_DESCRIPTION_MAX_LENGTH,
    )

    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None


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

    assignee_id: int | None = Field(default=None, gt=0)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator("title", "status", "priority", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError(FIELD_CANNOT_BE_NULL_MESSAGE)

        return value


class TaskResponse(BaseSchema):
    id: int
    project_id: int
    assignee_id: int | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_by: int
    created_at: datetime


class TaskListResponse(BaseSchema):
    items: list[TaskResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(ge=0)
