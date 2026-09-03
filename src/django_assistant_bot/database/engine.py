from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import Engine, event
from sqlalchemy.engine import URL
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy import create_engine

from django_assistant_bot.core.environment import EnvironmentSettings


def build_database_url(
    database_path: Path,
) -> SQLAlchemyURL:
    """
    Build a SQLAlchemy SQLite URL safely.

    Using URL.create avoids platform-specific escaping issues,
    especially on Windows paths.
    """

    return URL.create(
        drivername="sqlite+pysqlite",
        database=str(database_path),
    )


def create_database_engine(
    settings: EnvironmentSettings,
) -> Engine:
    """
    Create the application's SQLAlchemy engine.
    """

    database_path = settings.database_path

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    database_url = build_database_url(
        database_path,
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={
            "timeout": (settings.sqlite_timeout_seconds),
        },
    )

    _register_sqlite_events(
        engine=engine,
        timeout_seconds=(settings.sqlite_timeout_seconds),
    )

    return engine


def _register_sqlite_events(
    *,
    engine: Engine,
    timeout_seconds: float,
) -> None:
    """
    Configure SQLite connections.

    Applied to every DB-API connection created by SQLAlchemy.
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

            cursor.execute(f"PRAGMA busy_timeout = " f"{busy_timeout_ms};")

        finally:
            cursor.close()
