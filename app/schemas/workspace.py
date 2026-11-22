from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    USER_EMAIL_MAX_LENGTH,
    WORKSPACE_NAME_MAX_LENGTH,
)
from app.core.messages import (
    WORKSPACE_NAME_EMPTY_MESSAGE,
    WORKSPACE_OWNER_ROLE_NOT_ALLOWED_MESSAGE,
)
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.base import BaseSchema


class WorkspaceCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=WORKSPACE_NAME_MAX_LENGTH)


class WorkspaceUpdate(BaseSchema):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=WORKSPACE_NAME_MAX_LENGTH,
    )

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError(WORKSPACE_NAME_EMPTY_MESSAGE)

        return value


class WorkspaceResponse(BaseSchema):
    id: int
    name: str
    owner_id: int
    created_at: datetime


class WorkspaceListResponse(BaseSchema):
    items: list[WorkspaceResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class WorkspaceMemberCreate(BaseSchema):
    email: EmailStr = Field(max_length=USER_EMAIL_MAX_LENGTH)
    role: WorkspaceRole = WorkspaceRole.VIEWER

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("role")
    @classmethod
    def reject_owner_role(cls, value: WorkspaceRole) -> WorkspaceRole:
        if value == WorkspaceRole.OWNER:
            raise ValueError(WORKSPACE_OWNER_ROLE_NOT_ALLOWED_MESSAGE)

        return value


class WorkspaceMemberResponse(BaseSchema):
    user_id: int
    email: EmailStr
    full_name: str
    role: WorkspaceRole

    @classmethod
    def from_membership(
        cls,
        membership: WorkspaceMember,
        user: User,
    ) -> "WorkspaceMemberResponse":
        return cls(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
        )


class WorkspaceMemberListResponse(BaseSchema):
    items: list[WorkspaceMemberResponse]


class WorkspaceMemberUpdate(BaseSchema):
    role: WorkspaceRole

    @field_validator("role")
    @classmethod
    def reject_owner_role(cls, value: WorkspaceRole) -> WorkspaceRole:
        if value == WorkspaceRole.OWNER:
            raise ValueError("Cannot assign OWNER role to a workspace member.")

        return value
