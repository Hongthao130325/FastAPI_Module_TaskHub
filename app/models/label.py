from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import LABEL_COLOR_MAX_LENGTH, LABEL_NAME_MAX_LENGTH
from app.db.base import Base


class Label(Base):
    __tablename__ = "labels"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_labels_project_id_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(LABEL_NAME_MAX_LENGTH),
        nullable=False,
    )

    color: Mapped[str] = mapped_column(
        String(LABEL_COLOR_MAX_LENGTH),
        nullable=False,
    )
