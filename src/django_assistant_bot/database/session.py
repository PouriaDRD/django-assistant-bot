from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


class SessionManager:
    """
    Owns the SQLAlchemy session factory.

    Sessions are short-lived and created per operation.
    """

    def __init__(
        self,
        engine: Engine,
    ) -> None:
        self._factory = sessionmaker[Session](
            bind=engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session(
        self,
    ) -> Iterator[Session]:
        """
        Open a session without automatically committing.

        Useful for read operations.
        """

        session = self._factory()

        try:
            yield session

        finally:
            session.close()

    @contextmanager
    def transaction(
        self,
    ) -> Iterator[Session]:
        """
        Open a transactional session.

        Commits on success and rolls back on failure.
        """

        session = self._factory()

        try:
            yield session

            session.commit()

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()
