from __future__ import annotations

from unittest.mock import (
    MagicMock,
)

from sqlalchemy.exc import (
    SQLAlchemyError,
)

from django_assistant_bot.services.database_health import (
    DatabaseHealthService,
)


def test_database_is_healthy() -> None:
    sessions = MagicMock()

    session = MagicMock()

    sessions.session.return_value.__enter__.return_value = session

    service = DatabaseHealthService(
        sessions,
    )

    result = service.is_healthy()

    assert result is True

    session.execute.assert_called_once()


def test_database_is_unhealthy_when_query_fails() -> None:
    sessions = MagicMock()

    session = MagicMock()

    sessions.session.return_value.__enter__.return_value = session

    session.execute.side_effect = SQLAlchemyError("database unavailable")

    service = DatabaseHealthService(
        sessions,
    )

    result = service.is_healthy()

    assert result is False
