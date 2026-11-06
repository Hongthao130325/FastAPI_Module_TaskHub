from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        min_length=1,
        max_length=200
    )

    description: str | None = None


class TaskUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200
    )

    description: str | None = None
    is_completed: bool | None = None

    @field_validator("title", "is_completed", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")

        return value


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    is_completed: bool