from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from django_assistant_bot.database.session import (
    SessionManager,
)

logger = logging.getLogger(
    __name__,
)


class DatabaseHealthService:
    """
    Check application database connectivity.

    Health checks are read-only and intentionally lightweight.
    """

    def __init__(
        self,
        sessions: SessionManager,
    ) -> None:
        self._sessions = sessions

    def is_healthy(
        self,
    ) -> bool:
        """
        Return whether the application database is reachable.
        """

        try:
            with self._sessions.session() as session:
                session.execute(text("SELECT 1"))

            return True

        except SQLAlchemyError as exc:
            logger.warning(
                "Database health check failed: %s",
                exc,
            )

            return False


__all__ = [
    "DatabaseHealthService",
]
