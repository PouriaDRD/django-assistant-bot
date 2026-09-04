from __future__ import annotations

import sqlite3
from pathlib import (
    Path,
)
from threading import (
    Barrier,
    Lock,
    Thread,
)
from time import (
    sleep,
)

from sqlalchemy import (
    Engine,
    Integer,
    String,
    create_engine,
    event,
    select,
)
from sqlalchemy.engine.interfaces import (
    DBAPIConnection,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from django_assistant_bot.database.session import (
    SessionManager,
)

# =========================================================
# STRESS CONFIGURATION
# =========================================================


WRITER_COUNT = 16

WRITES_PER_WORKER = 25

READER_COUNT = 16

READS_PER_WORKER = 50

SQLITE_TIMEOUT_SECONDS = 5.0

WAIT_TIMEOUT_SECONDS = 15.0


# =========================================================
# TEST MODEL
# =========================================================


class Base(DeclarativeBase):
    pass


class StressRecord(Base):
    __tablename__ = "stress_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


# =========================================================
# ENGINE BUILDER
# =========================================================


def build_engine(
    database_path: Path,
) -> Engine:
    """
    Build a temporary SQLite engine using the same important
    runtime PRAGMA settings as the application database.
    """

    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        connect_args={
            "timeout": SQLITE_TIMEOUT_SECONDS,
        },
    )

    busy_timeout_ms = int(SQLITE_TIMEOUT_SECONDS * 1000)

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

    return engine


# =========================================================
# HELPERS
# =========================================================


def count_records(
    sessions: SessionManager,
) -> int:
    with sessions.session() as session:
        return len(session.scalars(select(StressRecord)).all())


# =========================================================
# MULTI-WRITER CONTENTION
# =========================================================


def test_many_concurrent_writers_complete_without_corruption(
    tmp_path: Path,
) -> None:
    """
    Many threads write to the same SQLite database.

    SQLite still serializes writers internally, but WAL +
    busy_timeout should allow the workers to make progress
    instead of failing immediately with "database is locked".
    """

    database_path = tmp_path / "writer-contention.sqlite3"

    engine = build_engine(
        database_path,
    )

    Base.metadata.create_all(
        engine,
    )

    sessions = SessionManager(
        engine,
    )

    start_barrier = Barrier(
        WRITER_COUNT,
    )

    error_lock = Lock()

    errors: list[BaseException] = []

    def writer(
        worker_index: int,
    ) -> None:
        try:
            start_barrier.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            for item_index in range(WRITES_PER_WORKER):
                with sessions.transaction() as session:
                    session.add(
                        StressRecord(
                            value=(f"worker-{worker_index}-" f"item-{item_index}")
                        )
                    )

        except BaseException as exc:
            with error_lock:
                errors.append(
                    exc,
                )

    threads = [
        Thread(
            target=writer,
            args=(worker_index,),
            name=(f"sqlite-writer-" f"{worker_index}"),
        )
        for worker_index in range(WRITER_COUNT)
    ]

    try:
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

        assert all(not thread.is_alive() for thread in threads)

        assert errors == []

        expected_records = WRITER_COUNT * WRITES_PER_WORKER

        assert (
            count_records(
                sessions,
            )
            == expected_records
        )

    finally:
        engine.dispose()


# =========================================================
# READ / WRITE CONTENTION
# =========================================================


def test_readers_remain_usable_while_writers_are_active(
    tmp_path: Path,
) -> None:
    """
    Stress readers and writers at the same time.

    WAL should allow readers to continue operating while
    write transactions are happening.
    """

    database_path = tmp_path / "read-write-contention.sqlite3"

    engine = build_engine(
        database_path,
    )

    Base.metadata.create_all(
        engine,
    )

    sessions = SessionManager(
        engine,
    )

    total_workers = WRITER_COUNT + READER_COUNT

    start_barrier = Barrier(
        total_workers,
    )

    error_lock = Lock()

    errors: list[BaseException] = []

    read_count_lock = Lock()

    successful_reads = 0

    def writer(
        worker_index: int,
    ) -> None:
        try:
            start_barrier.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            for item_index in range(WRITES_PER_WORKER):
                with sessions.transaction() as session:
                    session.add(
                        StressRecord(value=(f"writer-{worker_index}-" f"{item_index}"))
                    )

                sleep(0.001)

        except BaseException as exc:
            with error_lock:
                errors.append(
                    exc,
                )

    def reader() -> None:
        nonlocal successful_reads

        try:
            start_barrier.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            for _ in range(READS_PER_WORKER):
                with sessions.session() as session:
                    session.execute(select(StressRecord.id).limit(1)).all()

                with read_count_lock:
                    successful_reads += 1

        except BaseException as exc:
            with error_lock:
                errors.append(
                    exc,
                )

    writer_threads = [
        Thread(
            target=writer,
            args=(worker_index,),
            name=(f"sqlite-rw-writer-" f"{worker_index}"),
        )
        for worker_index in range(WRITER_COUNT)
    ]

    reader_threads = [
        Thread(
            target=reader,
            name=(f"sqlite-reader-" f"{reader_index}"),
        )
        for reader_index in range(READER_COUNT)
    ]

    threads = writer_threads + reader_threads

    try:
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

        assert all(not thread.is_alive() for thread in threads)

        assert errors == []

        assert successful_reads == (READER_COUNT * READS_PER_WORKER)

        expected_records = WRITER_COUNT * WRITES_PER_WORKER

        assert (
            count_records(
                sessions,
            )
            == expected_records
        )

    finally:
        engine.dispose()


# =========================================================
# TRANSACTION ROLLBACK
# =========================================================


def test_failed_transaction_rolls_back_and_database_remains_usable(
    tmp_path: Path,
) -> None:
    """
    A failed transaction must not leave partial state or
    poison subsequent database sessions.
    """

    database_path = tmp_path / "rollback.sqlite3"

    engine = build_engine(
        database_path,
    )

    Base.metadata.create_all(
        engine,
    )

    sessions = SessionManager(
        engine,
    )

    try:
        try:
            with sessions.transaction() as session:
                session.add(
                    StressRecord(
                        value="should-rollback",
                    )
                )

                session.flush()

                raise RuntimeError("simulated transaction failure")

        except RuntimeError:
            pass

        assert (
            count_records(
                sessions,
            )
            == 0
        )

        with sessions.transaction() as session:
            session.add(
                StressRecord(
                    value="after-rollback",
                )
            )

        assert (
            count_records(
                sessions,
            )
            == 1
        )

    finally:
        engine.dispose()


# =========================================================
# EXPLICIT LOCK CONTENTION
# =========================================================


def test_database_recovers_after_explicit_write_lock(
    tmp_path: Path,
) -> None:
    """
    Hold an explicit SQLite write lock and verify another
    writer waits for it, then succeeds after release.
    """

    database_path = tmp_path / "explicit-lock.sqlite3"

    engine = build_engine(
        database_path,
    )

    Base.metadata.create_all(
        engine,
    )

    sessions = SessionManager(
        engine,
    )

    lock_acquired = Barrier(2)

    release_writer = Barrier(2)

    errors: list[BaseException] = []

    error_lock = Lock()

    def locking_writer() -> None:
        connection = sqlite3.connect(
            database_path,
            timeout=(SQLITE_TIMEOUT_SECONDS),
        )

        try:
            connection.execute(
                ("PRAGMA busy_timeout = " f"{int(SQLITE_TIMEOUT_SECONDS * 1000)};")
            )

            connection.execute("BEGIN IMMEDIATE;")

            connection.execute(
                ("INSERT INTO stress_records " "(value) VALUES (?)"),
                ("locking-writer",),
            )

            lock_acquired.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            release_writer.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            connection.commit()

        except BaseException as exc:
            with error_lock:
                errors.append(
                    exc,
                )

        finally:
            connection.close()

    thread = Thread(
        target=locking_writer,
        name="sqlite-locking-writer",
    )

    try:
        thread.start()

        lock_acquired.wait(
            timeout=WAIT_TIMEOUT_SECONDS,
        )

        second_errors: list[BaseException] = []

        def second_writer() -> None:
            try:
                with sessions.transaction() as session:
                    session.add(
                        StressRecord(
                            value="waiting-writer",
                        )
                    )

            except BaseException as exc:
                second_errors.append(
                    exc,
                )

        second_thread = Thread(
            target=second_writer,
            name="sqlite-waiting-writer",
        )

        second_thread.start()

        # Give the second writer a brief opportunity to hit
        # SQLite's busy wait while the first transaction owns
        # the write lock.
        sleep(0.05)

        assert second_thread.is_alive()

        release_writer.wait(
            timeout=WAIT_TIMEOUT_SECONDS,
        )

        thread.join(
            timeout=WAIT_TIMEOUT_SECONDS,
        )

        second_thread.join(
            timeout=WAIT_TIMEOUT_SECONDS,
        )

        assert not thread.is_alive()

        assert not second_thread.is_alive()

        assert errors == []

        assert second_errors == []

        assert (
            count_records(
                sessions,
            )
            == 2
        )

    finally:
        engine.dispose()
