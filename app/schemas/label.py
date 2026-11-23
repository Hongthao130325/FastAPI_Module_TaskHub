from pydantic import ConfigDict, Field, PositiveInt, field_validator

from app.core.constants import (
    LABEL_COLOR_MAX_LENGTH,
    LABEL_NAME_MAX_LENGTH,
    MAX_PAGE_SIZE,
)
from app.schemas.base import BaseSchema


class LabelCreate(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=LABEL_NAME_MAX_LENGTH)
    color: str = Field(
        min_length=LABEL_COLOR_MAX_LENGTH,
        max_length=LABEL_COLOR_MAX_LENGTH,
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )


class LabelUpdate(BaseSchema):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=LABEL_NAME_MAX_LENGTH,
    )
    color: str | None = Field(
        default=None,
        min_length=LABEL_COLOR_MAX_LENGTH,
        max_length=LABEL_COLOR_MAX_LENGTH,
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )

    @field_validator("name", "color", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("Field cannot be null.")

        return value


class LabelResponse(BaseSchema):
    id: PositiveInt
    project_id: PositiveInt
    name: str
    color: str


class LabelListResponse(BaseSchema):
    items: list[LabelResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=MAX_PAGE_SIZE)
