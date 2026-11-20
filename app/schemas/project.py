from datetime import datetime

from pydantic import Field, field_validator

from app.core.constants import PROJECT_NAME_MAX_LENGTH
from app.models.enums import ProjectStatus
from app.schemas.base import BaseSchema


class ProjectCreate(BaseSchema):
    workspace_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=PROJECT_NAME_MAX_LENGTH)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Project name cannot be empty.")

        return value


class ProjectUpdate(BaseSchema):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=PROJECT_NAME_MAX_LENGTH,
    )
    description: str | None = None

    @field_validator("name")
    @classmethod
    def reject_null_or_empty_name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("Project name cannot be empty.")

        return value.strip()


class ProjectResponse(BaseSchema):
    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime


class ProjectListResponse(BaseSchema):
    items: list[ProjectResponse]
