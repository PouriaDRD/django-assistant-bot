from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    String,
    Text,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from django_assistant_bot.database.base import Base
from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)

if TYPE_CHECKING:
    from database.models.backup_history import (
        BackupHistoryModel,
    )


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


def generate_project_id() -> str:
    return uuid4().hex


class ProjectModel(Base):
    """
    Registered Django project.
    """

    __tablename__ = "projects"

    __table_args__ = (
        CheckConstraint(
            "schedule_interval >= 1",
            name="schedule_interval_positive",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_project_id,
    )

    name: Mapped[str] = mapped_column(
        String(
            200,
            collation="NOCASE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    database_type: Mapped[DatabaseType] = mapped_column(
        Enum(
            DatabaseType,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=DatabaseType.SQLITE,
        server_default=text("'sqlite'"),
    )

    database_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    media_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    media_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    schedule_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    schedule_interval: Mapped[int] = mapped_column(
        nullable=False,
        default=6,
        server_default=text("6"),
    )

    schedule_unit: Mapped[ScheduleUnit] = mapped_column(
        Enum(
            ScheduleUnit,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=ScheduleUnit.HOURS,
        server_default=text("'hours'"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    backup_history: Mapped[list[BackupHistoryModel]] = relationship(
        back_populates="project",
        cascade=("all, delete-orphan"),
        passive_deletes=True,
    )
