from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from django_assistant_bot.database.base import Base
from django_assistant_bot.database.models.enums import BackupStatus

if TYPE_CHECKING:
    from database.models.project import ProjectModel


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


def generate_backup_id() -> str:
    return uuid4().hex


class BackupHistoryModel(Base):
    """
    Persistent history of project backup attempts.
    """

    __tablename__ = "backup_history"

    __table_args__ = (
        CheckConstraint(
            "database_size_bytes >= 0",
            name="database_size_non_negative",
        ),
        CheckConstraint(
            "media_size_bytes >= 0",
            name="media_size_non_negative",
        ),
        CheckConstraint(
            "archive_size_bytes >= 0",
            name="archive_size_non_negative",
        ),
        CheckConstraint(
            "media_file_count >= 0",
            name="media_file_count_non_negative",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_backup_id,
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[BackupStatus] = mapped_column(
        Enum(
            BackupStatus,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        index=True,
    )

    archive_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    database_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    media_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    archive_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    media_file_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    checksum_algorithm: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    checksum_value: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    project: Mapped[ProjectModel] = relationship(
        back_populates="backup_history",
    )
