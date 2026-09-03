from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from django_assistant_bot.database.base import Base
from django_assistant_bot.database.session import SessionManager

import django_assistant_bot.database.models  # noqa: F401


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    try:
        yield engine

    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def session_manager(
    engine: Engine,
) -> SessionManager:
    return SessionManager(
        engine,
    )
