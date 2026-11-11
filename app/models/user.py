from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    USER_EMAIL_MAX_LENGTH,
    USER_FULL_NAME_MAX_LENGTH,
    USER_PASSWORD_HASH_MAX_LENGTH,
)
from app.db.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    email: Mapped[str] = mapped_column(
        String(USER_EMAIL_MAX_LENGTH),
        unique=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(USER_FULL_NAME_MAX_LENGTH),
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(USER_PASSWORD_HASH_MAX_LENGTH),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.MEMBER,
        server_default=UserRole.MEMBER.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
