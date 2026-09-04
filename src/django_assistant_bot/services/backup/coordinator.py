from __future__ import annotations

import logging
from dataclasses import replace
from datetime import (
    datetime,
    timezone,
)
from threading import Lock
from typing import Protocol

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.schemas.backup import (
    BackupHistoryCreateSchema,
    BackupHistorySchema,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.services.backup.exceptions import (
    BackupAlreadyRunningError,
    BackupDisabledError,
    BackupExecutionError,
    BackupHistoryError,
    BotDisabledError,
    ProjectBackupDisabledError,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    BackupRetentionSummary,
)
from django_assistant_bot.services.backup.retention import (
    RetentionResult,
)
from django_assistant_bot.services.backup.service import (
    BackupService,
)

logger = logging.getLogger(
    __name__,
)


# =========================================================
# DEPENDENCY CONTRACTS
# =========================================================


class ProjectReader(Protocol):
    """
    Minimal project dependency required by the coordinator.
    """

    def get_project(
        self,
        project_id: str,
    ) -> ProjectSchema: ...


class SettingsReader(Protocol):
    """
    Minimal settings dependency required by the coordinator.
    """

    def get_settings(
        self,
    ) -> AppSettingsSchema: ...


class BackupHistoryWriter(Protocol):
    """
    Minimal backup-history dependency required by the
    coordinator.
    """

    def create(
        self,
        data: BackupHistoryCreateSchema,
    ) -> BackupHistorySchema: ...


class BackupRunner(Protocol):
    """
    Something capable of executing a project backup.
    """

    def backup_project(
        self,
        project: ProjectSchema,
    ) -> BackupResult: ...


class BackupRunnerFactory(Protocol):
    """
    Factory used to build a backup runner from runtime
    application settings.
    """

    def __call__(
        self,
        settings: AppSettingsSchema,
    ) -> BackupRunner: ...


class RetentionRunner(Protocol):
    """
    Minimal retention dependency required by coordinator.
    """

    def cleanup(
        self,
        *,
        project_id: str,
        keep_last: int,
    ) -> RetentionResult: ...


# =========================================================
# DEFAULT FACTORY
# =========================================================


def create_backup_service(
    settings: AppSettingsSchema,
) -> BackupService:
    """
    Build BackupService from persisted runtime settings.

    Retention is intentionally handled by BackupCoordinator
    after successful backup-history persistence.
    """

    return BackupService(
        backup_directory=(settings.backup_directory),
        compression_level=(settings.compression_level),
    )


# =========================================================
# COORDINATOR
# =========================================================


class BackupCoordinator:
    """
    Coordinate complete application-level backup execution.

    Responsibilities:
    - load project configuration
    - load application settings
    - reject execution when bot is globally disabled
    - reject backups when globally disabled
    - prevent concurrent backups for the same project
    - execute BackupService
    - persist successful backup history
    - persist failed backup history
    - apply retention after successful history persistence

    Retention is best-effort.

    A retention failure must never convert an already
    successful backup into a failed backup.

    This coordinator intentionally does not know anything
    about Telegram or the scheduler.
    """

    def __init__(
        self,
        *,
        projects: ProjectReader,
        settings: SettingsReader,
        history: BackupHistoryWriter,
        retention: RetentionRunner,
        runner_factory: BackupRunnerFactory = (create_backup_service),
    ) -> None:
        self._projects = projects

        self._settings = settings

        self._history = history

        self._retention = retention

        self._runner_factory = runner_factory

        self._running_projects: set[str] = set()

        self._running_projects_lock = Lock()

    # =====================================================
    # PUBLIC API
    # =====================================================

    def run(
        self,
        project_id: str,
    ) -> BackupResult:
        """
        Execute a complete backup operation for a project.
        """

        normalized_project_id = project_id.strip()

        if not normalized_project_id:
            raise ValueError("Project ID cannot be empty.")

        self._acquire_project(
            normalized_project_id,
        )

        try:
            return self._run_backup(
                normalized_project_id,
            )

        finally:
            self._release_project(
                normalized_project_id,
            )

    def is_running(
        self,
        project_id: str,
    ) -> bool:
        """
        Return whether the project currently has a backup
        running in this process.
        """

        normalized_project_id = project_id.strip()

        if not normalized_project_id:
            return False

        with self._running_projects_lock:
            return normalized_project_id in self._running_projects

    # =====================================================
    # EXECUTION
    # =====================================================

    def _run_backup(
        self,
        project_id: str,
    ) -> BackupResult:
        """
        Run one backup after validating application state.
        """

        settings = self._settings.get_settings()

        if not settings.bot_enabled:
            raise BotDisabledError("Application activity is disabled.")

        if not settings.backup_enabled:
            raise BackupDisabledError("Backup functionality is disabled.")

        project = self._projects.get_project(
            project_id,
        )

        if not project.enabled:
            raise ProjectBackupDisabledError("Project is disabled: " f"{project.name}")

        started_at = datetime.now(
            timezone.utc,
        )

        runner = self._runner_factory(
            settings,
        )

        try:
            result = runner.backup_project(
                project,
            )

        except ProjectBackupDisabledError:
            raise

        except Exception as exc:
            finished_at = datetime.now(
                timezone.utc,
            )

            self._record_failure(
                project=project,
                error=exc,
                started_at=started_at,
                finished_at=finished_at,
            )

            raise BackupExecutionError(
                "Backup failed for project: " f"{project.name}"
            ) from exc

        # -------------------------------------------------
        # Persist successful backup before retention.
        # -------------------------------------------------

        self._record_success(
            result,
        )

        # -------------------------------------------------
        # Retention is best-effort.
        # -------------------------------------------------

        if not settings.retention_enabled:
            return result

        retention_summary = self._apply_retention(
            project_id=project.id,
            keep_last=(settings.retention_keep_last),
        )

        return replace(
            result,
            retention=retention_summary,
        )

    # =====================================================
    # RETENTION
    # =====================================================

    def _apply_retention(
        self,
        *,
        project_id: str,
        keep_last: int,
    ) -> BackupRetentionSummary:
        """
        Apply retention after a successful backup.

        Cleanup failure must never change the successful
        backup result.
        """

        try:
            result = self._retention.cleanup(
                project_id=project_id,
                keep_last=keep_last,
            )

        except Exception:
            logger.exception(
                "Backup retention cleanup failed " "for project %s.",
                project_id,
            )

            return BackupRetentionSummary(
                keep_last=keep_last,
                cleanup_failed=True,
            )

        removed_count = len(result.removed_history_ids)

        failed_archive_count = len(result.failed_archives)

        if removed_count:
            logger.info(
                "Backup retention removed %d "
                "backup history record(s) "
                "for project %s.",
                removed_count,
                project_id,
            )

        if failed_archive_count:
            logger.warning(
                "Backup retention could not remove " "%d archive(s) for project %s.",
                failed_archive_count,
                project_id,
            )

        return BackupRetentionSummary(
            keep_last=keep_last,
            successful_before=(result.successful_before),
            successful_after=(result.successful_after),
            removed_count=removed_count,
            failed_archive_count=(failed_archive_count),
            cleanup_failed=False,
        )

    # =====================================================
    # HISTORY
    # =====================================================

    def _record_success(
        self,
        result: BackupResult,
    ) -> None:
        """
        Persist successful backup history.
        """

        data = BackupHistoryCreateSchema(
            project_id=result.project_id,
            status=BackupStatus.SUCCESS,
            archive_path=result.archive_path,
            database_size_bytes=(result.database_size_bytes),
            media_size_bytes=(result.media_size_bytes),
            archive_size_bytes=(result.archive_size_bytes),
            media_file_count=(result.media_file_count),
            checksum_algorithm=(result.checksum.algorithm),
            checksum_value=(result.checksum.value),
            error_message=None,
            started_at=result.started_at,
            finished_at=result.finished_at,
        )

        try:
            self._history.create(
                data,
            )

        except Exception as exc:
            raise BackupHistoryError(
                "Backup succeeded but history " "could not be recorded."
            ) from exc

    def _record_failure(
        self,
        *,
        project: ProjectSchema,
        error: Exception,
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        """
        Persist a genuine backup execution failure.
        """

        data = BackupHistoryCreateSchema(
            project_id=project.id,
            status=BackupStatus.FAILED,
            archive_path=None,
            database_size_bytes=0,
            media_size_bytes=0,
            archive_size_bytes=0,
            media_file_count=0,
            checksum_algorithm=None,
            checksum_value=None,
            error_message=str(
                error,
            ),
            started_at=started_at,
            finished_at=finished_at,
        )

        try:
            self._history.create(
                data,
            )

        except Exception as history_error:
            error.add_note(
                "Additionally, failed to persist "
                "backup failure history: "
                f"{history_error}"
            )

    # =====================================================
    # CONCURRENCY
    # =====================================================

    def _acquire_project(
        self,
        project_id: str,
    ) -> None:
        """
        Atomically mark a project as running.
        """

        with self._running_projects_lock:
            if project_id in self._running_projects:
                raise BackupAlreadyRunningError(
                    "A backup is already running " "for project: " f"{project_id}"
                )

            self._running_projects.add(
                project_id,
            )

    def _release_project(
        self,
        project_id: str,
    ) -> None:
        """
        Release the project's in-process backup lock.
        """

        with self._running_projects_lock:
            self._running_projects.discard(
                project_id,
            )


__all__ = [
    "BackupCoordinator",
    "BackupHistoryWriter",
    "BackupRunner",
    "BackupRunnerFactory",
    "ProjectReader",
    "RetentionRunner",
    "SettingsReader",
    "create_backup_service",
]
