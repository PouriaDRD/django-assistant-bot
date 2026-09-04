from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import (
    Path,
)
from threading import (
    Barrier,
    Lock,
    Thread,
)

import pytest

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.repositories.exceptions import (
    PersistenceError,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.services.backup.exceptions import (
    RetentionError,
)
from django_assistant_bot.services.backup.retention import (
    RetentionService,
)

# =========================================================
# STRESS CONFIGURATION
# =========================================================


LARGE_HISTORY_COUNT = 250

LARGE_KEEP_LAST = 10

CONCURRENT_PROJECT_COUNT = 8

HISTORIES_PER_PROJECT = 50

CONCURRENT_KEEP_LAST = 5

WAIT_TIMEOUT_SECONDS = 15.0


# =========================================================
# TEST REPOSITORY
# =========================================================


class ThreadSafeRetentionRepository:
    """
    Thread-safe in-memory repository for retention stress tests.

    Histories are stored newest-first to match the retention
    service contract.
    """

    def __init__(
        self,
        histories: dict[
            str,
            list[BackupHistorySchema],
        ],
    ) -> None:
        self._lock = Lock()

        self._histories = {
            project_id: list(
                project_histories,
            )
            for (
                project_id,
                project_histories,
            ) in histories.items()
        }

        self._fail_delete_once_for: set[str] = set()

        self.deleted_ids: list[str] = []

    def list_successful_for_project(
        self,
        project_id: str,
    ) -> list[BackupHistorySchema]:
        with self._lock:
            return list(
                self._histories.get(
                    project_id,
                    [],
                )
            )

    def delete_by_id(
        self,
        history_id: str,
    ) -> bool:
        with self._lock:
            if history_id in self._fail_delete_once_for:
                self._fail_delete_once_for.remove(
                    history_id,
                )

                raise PersistenceError(
                    ("Simulated retention history " "delete failure.")
                )

            for histories in self._histories.values():
                for index, history in enumerate(histories):
                    if history.id != history_id:
                        continue

                    del histories[index]

                    self.deleted_ids.append(
                        history_id,
                    )

                    return True

            return False

    def fail_delete_once(
        self,
        history_id: str,
    ) -> None:
        with self._lock:
            self._fail_delete_once_for.add(
                history_id,
            )

    def project_histories(
        self,
        project_id: str,
    ) -> list[BackupHistorySchema]:
        with self._lock:
            return list(
                self._histories.get(
                    project_id,
                    [],
                )
            )


# =========================================================
# BUILDERS
# =========================================================


def build_history(
    *,
    history_id: str,
    project_id: str,
    archive_path: Path,
    started_at: datetime,
) -> BackupHistorySchema:
    return BackupHistorySchema(
        id=history_id,
        project_id=project_id,
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        database_size_bytes=1024,
        media_size_bytes=2048,
        archive_size_bytes=1536,
        media_file_count=5,
        checksum_algorithm="sha256",
        checksum_value=(f"checksum-{history_id}"),
        error_message=None,
        started_at=started_at,
        finished_at=started_at,
    )


def build_project_histories(
    tmp_path: Path,
    *,
    project_id: str,
    count: int,
) -> list[BackupHistorySchema]:
    """
    Build newest-first successful backup histories.
    """

    project_directory = tmp_path / project_id

    project_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    now = datetime.now(
        timezone.utc,
    )

    histories: list[BackupHistorySchema] = []

    for index in range(count):
        archive_path = project_directory / f"backup-{index}.zip"

        archive_path.write_bytes((f"backup-{project_id}-{index}").encode())

        histories.append(
            build_history(
                history_id=(f"{project_id}-history-{index}"),
                project_id=project_id,
                archive_path=archive_path,
                started_at=(
                    now
                    - timedelta(
                        seconds=index,
                    )
                ),
            )
        )

    return histories


# =========================================================
# LARGE HISTORY SET
# =========================================================


def test_retention_handles_large_history_set(
    tmp_path: Path,
) -> None:
    """
    Cleanup a relatively large successful backup history set.

    Expected:

    - newest N backups remain
    - every expired archive is removed
    - every expired history is removed
    - no unexpected failures occur
    """

    project_id = "large-history-project"

    histories = build_project_histories(
        tmp_path,
        project_id=project_id,
        count=LARGE_HISTORY_COUNT,
    )

    repository = ThreadSafeRetentionRepository(
        {
            project_id: histories,
        }
    )

    service = RetentionService(
        repository,
    )

    result = service.cleanup(
        project_id=project_id,
        keep_last=LARGE_KEEP_LAST,
    )

    expected_removed = LARGE_HISTORY_COUNT - LARGE_KEEP_LAST

    assert result.successful_before == LARGE_HISTORY_COUNT

    assert result.successful_after == LARGE_KEEP_LAST

    assert len(result.removed_archives) == expected_removed

    assert len(result.removed_history_ids) == expected_removed

    assert result.failed_archives == ()

    remaining = repository.project_histories(
        project_id,
    )

    assert len(remaining) == LARGE_KEEP_LAST

    # -----------------------------------------------------
    # NEWEST ARCHIVES MUST STILL EXIST
    # -----------------------------------------------------

    for history in histories[:LARGE_KEEP_LAST]:
        assert history.archive_path is not None

        assert history.archive_path.exists()

    # -----------------------------------------------------
    # EXPIRED ARCHIVES MUST BE GONE
    # -----------------------------------------------------

    for history in histories[LARGE_KEEP_LAST:]:
        assert history.archive_path is not None

        assert not (history.archive_path.exists())


# =========================================================
# FILESYSTEM FAILURE
# =========================================================


def test_retention_continues_after_multiple_archive_delete_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Multiple archive deletion failures must not abort the
    entire cleanup.

    Histories whose archives cannot be removed must remain,
    while independent expired backups should still be cleaned.
    """

    project_id = "filesystem-failure-project"

    histories = build_project_histories(
        tmp_path,
        project_id=project_id,
        count=20,
    )

    repository = ThreadSafeRetentionRepository(
        {
            project_id: histories,
        }
    )

    service = RetentionService(
        repository,
    )

    # Keep the newest five.
    expired = histories[5:]

    failing_paths = {
        expired[1].archive_path,
        expired[5].archive_path,
        expired[9].archive_path,
    }

    assert None not in failing_paths

    original_unlink = Path.unlink

    def controlled_unlink(
        path: Path,
        *args: object,
        **kwargs: object,
    ) -> None:
        del args
        del kwargs

        if path in failing_paths:
            raise PermissionError(("Simulated archive " "permission failure."))

        original_unlink(
            path,
        )

    monkeypatch.setattr(
        Path,
        "unlink",
        controlled_unlink,
    )

    result = service.cleanup(
        project_id=project_id,
        keep_last=5,
    )

    # -----------------------------------------------------
    # THREE ARCHIVES FAILED TO DELETE
    # -----------------------------------------------------

    assert set(result.failed_archives) == failing_paths

    assert len(result.failed_archives) == 3

    # -----------------------------------------------------
    # ALL OTHER EXPIRED HISTORIES WERE REMOVED
    # -----------------------------------------------------

    expected_removed = len(expired) - len(failing_paths)

    assert len(result.removed_history_ids) == expected_removed

    assert len(result.removed_archives) == expected_removed

    # -----------------------------------------------------
    # FAILED ARCHIVES AND HISTORIES MUST REMAIN
    # -----------------------------------------------------

    remaining = repository.project_histories(
        project_id,
    )

    remaining_ids = {history.id for history in remaining}

    # Five retained newest backups plus three failures.
    assert len(remaining) == 8

    for history in expired:
        archive_path = history.archive_path

        assert archive_path is not None

        if archive_path in failing_paths:
            assert archive_path.exists()

            assert history.id in remaining_ids

        else:
            assert not (archive_path.exists())

            assert history.id not in remaining_ids


# =========================================================
# DATABASE FAILURE + RECOVERY
# =========================================================


def test_retention_recovers_after_history_delete_failure(
    tmp_path: Path,
) -> None:
    """
    Simulate persistence failure after an archive has already
    been removed.

    The first cleanup should fail with RetentionError.

    On retry, the now-missing archive should be treated as
    stale history and the cleanup should recover normally.
    """

    project_id = "history-recovery-project"

    histories = build_project_histories(
        tmp_path,
        project_id=project_id,
        count=8,
    )

    repository = ThreadSafeRetentionRepository(
        {
            project_id: histories,
        }
    )

    service = RetentionService(
        repository,
    )

    # Keep two newest histories.
    #
    # Expired order:
    # history-2
    # history-3
    # history-4
    # ...
    #
    # Make deletion of history-3 fail once.
    failing_history = histories[3]

    repository.fail_delete_once(
        failing_history.id,
    )

    # -----------------------------------------------------
    # FIRST CLEANUP FAILS MIDWAY
    # -----------------------------------------------------

    with pytest.raises(
        RetentionError,
        match="history cleanup",
    ):
        service.cleanup(
            project_id=project_id,
            keep_last=2,
        )

    first_expired = histories[2]

    assert first_expired.archive_path is not None

    assert failing_history.archive_path is not None

    # history-2 completed successfully.
    assert not (first_expired.archive_path.exists())

    # The failing archive was already deleted before the DB
    # delete failed.
    assert not (failing_history.archive_path.exists())

    current_ids = {
        history.id
        for history in repository.project_histories(
            project_id,
        )
    }

    assert first_expired.id not in current_ids

    # Persistence failed, so its history still exists.
    assert failing_history.id in current_ids

    # -----------------------------------------------------
    # SECOND CLEANUP MUST RECOVER
    # -----------------------------------------------------

    result = service.cleanup(
        project_id=project_id,
        keep_last=2,
    )

    remaining = repository.project_histories(
        project_id,
    )

    assert len(remaining) == 2

    assert {history.id for history in remaining} == {
        histories[0].id,
        histories[1].id,
    }

    assert result.successful_after == 2

    # The history whose archive was already gone should now
    # be removed successfully as stale history.
    assert failing_history.id in result.removed_history_ids


# =========================================================
# MULTI-PROJECT CONCURRENT CLEANUP
# =========================================================


def test_multiple_projects_can_run_retention_concurrently(
    tmp_path: Path,
) -> None:
    """
    Run retention for several different projects at once.

    Expected:

    - projects do not corrupt each other's histories
    - each project independently keeps its newest N backups
    - all expired files are removed
    - no worker remains stuck
    """

    project_ids = [
        f"retention-project-{index}" for index in range(CONCURRENT_PROJECT_COUNT)
    ]

    histories = {
        project_id: (
            build_project_histories(
                tmp_path,
                project_id=project_id,
                count=HISTORIES_PER_PROJECT,
            )
        )
        for project_id in project_ids
    }

    repository = ThreadSafeRetentionRepository(
        histories,
    )

    service = RetentionService(
        repository,
    )

    start_barrier = Barrier(
        CONCURRENT_PROJECT_COUNT,
    )

    result_lock = Lock()

    errors: list[BaseException] = []

    completed_projects: set[str] = set()

    def worker(
        project_id: str,
    ) -> None:
        try:
            start_barrier.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            result = service.cleanup(
                project_id=project_id,
                keep_last=(CONCURRENT_KEEP_LAST),
            )

            assert result.successful_after == CONCURRENT_KEEP_LAST

        except BaseException as exc:
            with result_lock:
                errors.append(
                    exc,
                )

        else:
            with result_lock:
                completed_projects.add(
                    project_id,
                )

    threads = [
        Thread(
            target=worker,
            args=(project_id,),
            name=("retention-stress-" f"{project_id}"),
        )
        for project_id in project_ids
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join(
            timeout=WAIT_TIMEOUT_SECONDS,
        )

    # -----------------------------------------------------
    # THREAD HEALTH
    # -----------------------------------------------------

    assert all(not thread.is_alive() for thread in threads)

    assert errors == []

    assert completed_projects == set(project_ids)

    # -----------------------------------------------------
    # PER-PROJECT INVARIANTS
    # -----------------------------------------------------

    for project_id in project_ids:
        remaining = repository.project_histories(
            project_id,
        )

        assert len(remaining) == CONCURRENT_KEEP_LAST

        expected_remaining = histories[project_id][:CONCURRENT_KEEP_LAST]

        assert {history.id for history in remaining} == {
            history.id for history in expected_remaining
        }

        # Newest archives remain.
        for history in expected_remaining:
            assert history.archive_path is not None

            assert history.archive_path.exists()

        # Expired archives are gone.
        for history in histories[project_id][CONCURRENT_KEEP_LAST:]:
            assert history.archive_path is not None

            assert not (history.archive_path.exists())
