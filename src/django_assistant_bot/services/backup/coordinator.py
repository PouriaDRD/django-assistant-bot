from __future__ import annotations

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
from django_assistant_bot.services.backup.models import (
    BackupResult,
)
from django_assistant_bot.services.backup.service import (
    BackupService,
)
from django_assistant_bot.services.backup.exceptions import (
    BackupAlreadyRunningError,
    BackupDisabledError,
    BackupExecutionError,
    BackupHistoryError,
    ProjectBackupDisabledError,
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


# =========================================================
# DEFAULT FACTORY
# =========================================================


def create_backup_service(
    settings: AppSettingsSchema,
) -> BackupService:
    """
    Build BackupService from persisted runtime settings.
    """

    return BackupService(
        backup_directory=(settings.backup_directory),
        compression_level=(settings.compression_level),
        retention_enabled=(settings.retention_enabled),
        keep_last=(settings.retention_keep_last),
    )


# =========================================================
# COORDINATOR
# =========================================================


class BackupCoordinator:
    """
    Coordinates complete application-level backup execution.

    Responsibilities:
    - load project configuration
    - load application backup settings
    - reject backups when globally disabled
    - prevent concurrent backups for the same project
    - execute BackupService
    - persist successful backup history
    - persist failed backup history

    This coordinator intentionally does not know anything
    about Telegram or the scheduler.
    """

    def __init__(
        self,
        *,
        projects: ProjectReader,
        settings: SettingsReader,
        history: BackupHistoryWriter,
        runner_factory: BackupRunnerFactory = (create_backup_service),
    ) -> None:
        self._projects = projects

        self._settings = settings

        self._history = history

        self._runner_factory = runner_factory

        self._running_projects: set[str] = set()

        self._running_projects_lock = Lock()

    # -----------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------

    def run(
        self,
        project_id: str,
    ) -> BackupResult:
        """
        Execute a complete backup operation for a project.

        Only one backup for the same project may run at
        the same time.

        Different projects may be backed up concurrently.
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

    # -----------------------------------------------------
    # EXECUTION
    # -----------------------------------------------------

    def _run_backup(self, project_id: str) -> BackupResult:
        project = self._projects.get_project(
            project_id,
        )

        if not project.enabled:
            raise ProjectBackupDisabledError("Project is disabled: " f"{project.name}")

        settings = self._settings.get_settings()

        if not settings.backup_enabled:
            raise BackupDisabledError("Backup functionality is disabled.")

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

        self._record_success(
            result,
        )

        return result

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    def _record_success(
        self,
        result: BackupResult,
    ) -> None:
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
            # The original backup error is more important
            # than a secondary history persistence failure.
            error.add_note(
                "Additionally, failed to persist "
                "backup failure history: "
                f"{history_error}"
            )

    # -----------------------------------------------------
    # CONCURRENCY
    # -----------------------------------------------------

    def _acquire_project(
        self,
        project_id: str,
    ) -> None:
        """
        Atomically mark a project as running.

        We intentionally reject duplicate execution instead
        of blocking until the previous backup finishes.
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
