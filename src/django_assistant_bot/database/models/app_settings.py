from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from django_assistant_bot.database.base import Base
from django_assistant_bot.database.models.enums import (
    CompressionFormat,
)


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


class AppSettingsModel(Base):
    """
    Singleton row containing runtime application settings.

    The table always uses id=1.
    """

    __tablename__ = "app_settings"

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="singleton_id",
        ),
        CheckConstraint(
            ("compression_level >= 0 " "AND compression_level <= 9"),
            name="compression_level_range",
        ),
        CheckConstraint(
            "retention_keep_last >= 1",
            name="retention_keep_last_positive",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        server_default=text("1"),
    )

    bot_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    backup_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    backup_directory: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="./backups",
        server_default=text("'./backups'"),
    )

    compression_format: Mapped[CompressionFormat] = mapped_column(
        Enum(
            CompressionFormat,
            native_enum=False,
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
        default=CompressionFormat.ZIP,
        server_default=text("'zip'"),
    )

    compression_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=6,
        server_default=text("6"),
    )

    retention_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    retention_keep_last: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default=text("10"),
    )

    proxy_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    proxy_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default=text("''"),
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
