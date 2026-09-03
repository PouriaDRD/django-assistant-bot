from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from django_assistant_bot.database.base import Base


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc,
    )


class AdminModel(Base):
    """
    Telegram administrator allowed to access the bot.
    """

    __tablename__ = "admins"

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
