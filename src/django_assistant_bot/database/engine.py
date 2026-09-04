from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import (
    Engine,
    create_engine,
    event,
)
from sqlalchemy.engine import (
    URL,
)
from sqlalchemy.engine.interfaces import (
    DBAPIConnection,
)
from sqlalchemy.engine.url import (
    URL as SQLAlchemyURL,
)

from django_assistant_bot.core.paths import (
    DATABASE_PATH,
)

# =========================================================
# SQLITE
# =========================================================


SQLITE_TIMEOUT_SECONDS = 10.0


# =========================================================
# URL
# =========================================================


def build_database_url(
    database_path: Path,
) -> SQLAlchemyURL:
    """
    Build a SQLAlchemy SQLite URL safely.

    Using URL.create avoids platform-specific escaping
    issues, especially on Windows paths.
    """

    return URL.create(
        drivername=("sqlite+pysqlite"),
        database=str(database_path),
    )


# =========================================================
# ENGINE
# =========================================================


def create_database_engine() -> Engine:
    """
    Create the application's SQLAlchemy engine.
    """

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    database_url = build_database_url(DATABASE_PATH)

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={
            "timeout": (SQLITE_TIMEOUT_SECONDS),
        },
    )

    _register_sqlite_events(
        engine=engine,
        timeout_seconds=(SQLITE_TIMEOUT_SECONDS),
    )

    return engine


# =========================================================
# SQLITE EVENTS
# =========================================================


def _register_sqlite_events(
    *,
    engine: Engine,
    timeout_seconds: float,
) -> None:
    """
    Configure SQLite connections.

    Applied to every DB-API connection created
    by SQLAlchemy.
    """

    busy_timeout_ms = int(timeout_seconds * 1000)

    @event.listens_for(
        engine,
        "connect",
    )
    def configure_sqlite_connection(
        dbapi_connection: DBAPIConnection,
        _connection_record: object,
    ) -> None:
        if not isinstance(
            dbapi_connection,
            sqlite3.Connection,
        ):
            return

        cursor = dbapi_connection.cursor()

        try:
            cursor.execute("PRAGMA foreign_keys = ON;")

            cursor.execute("PRAGMA journal_mode = WAL;")

            cursor.execute("PRAGMA synchronous = NORMAL;")

            cursor.execute(("PRAGMA busy_timeout = " f"{busy_timeout_ms};"))

        finally:
            cursor.close()


__all__ = [
    "SQLITE_TIMEOUT_SECONDS",
    "build_database_url",
    "create_database_engine",
]
