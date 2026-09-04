from __future__ import annotations

import platform
from pathlib import Path
from typing import Protocol

import psutil

from django_assistant_bot.schemas.admin import (
    AdminSchema,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.schemas.system_status import (
    LatestBackupStatusSchema,
    SchedulerRuntimeStatus,
    SystemStatusSchema,
)

# =========================================================
# DEPENDENCY CONTRACTS
# =========================================================


class SettingsReader(Protocol):
    """
    Minimal settings contract required by system status.
    """

    def get_settings(
        self,
    ) -> AppSettingsSchema: ...


class ProjectReader(Protocol):
    """
    Minimal project contract required by system status.
    """

    def list_projects(
        self,
    ) -> list[ProjectSchema]: ...


class AdminReader(Protocol):
    """
    Minimal administrator contract required by system status.
    """

    def list_admins(
        self,
    ) -> list[AdminSchema]: ...


class SchedulerReader(Protocol):
    """
    Minimal scheduler runtime contract required by system
    status.
    """

    @property
    def is_started(
        self,
    ) -> bool: ...

    @property
    def is_paused(
        self,
    ) -> bool: ...


class RuntimeReader(Protocol):
    """
    Minimal application-runtime contract required by
    system status.
    """

    def get_uptime_seconds(
        self,
    ) -> float: ...


class DatabaseHealthReader(Protocol):
    """
    Minimal database-health contract required by
    system status.
    """

    def is_healthy(
        self,
    ) -> bool: ...


class BackupHistoryReader(Protocol):
    """
    Minimal backup-history contract required by
    system status.
    """

    def get_latest(
        self,
    ) -> BackupHistorySchema | None: ...


# =========================================================
# SERVICE
# =========================================================


class SystemStatusService:
    """
    Build an application-wide runtime status snapshot.

    The service exposes application state together with host
    operating-system, backup and resource information.

    It remains independent from Telegram.
    """

    def __init__(
        self,
        *,
        settings: SettingsReader,
        projects: ProjectReader,
        admins: AdminReader,
        scheduler: SchedulerReader,
        runtime: RuntimeReader,
        database_health: DatabaseHealthReader,
        backup_history: BackupHistoryReader,
    ) -> None:
        self._settings = settings

        self._projects = projects

        self._admins = admins

        self._scheduler = scheduler

        self._runtime = runtime

        self._database_health = database_health

        self._backup_history = backup_history

    def get_status(
        self,
    ) -> SystemStatusSchema:
        """
        Return the current application and host runtime status.
        """

        settings = self._settings.get_settings()

        projects = self._projects.list_projects()

        admins = self._admins.list_admins()

        latest_backup = self._backup_history.get_latest()

        enabled_project_count = sum(1 for project in projects if project.enabled)

        scheduled_project_count = sum(
            1 for project in projects if (project.enabled and project.schedule.enabled)
        )

        project_names = {project.id: project.name for project in projects}

        memory = psutil.virtual_memory()

        disk = psutil.disk_usage(self._get_disk_root())

        cpu_physical_cores = psutil.cpu_count(
            logical=False,
        )

        cpu_logical_cores = (
            psutil.cpu_count(
                logical=True,
            )
            or 1
        )

        return SystemStatusSchema(
            # ---------------------------------------------
            # APPLICATION
            # ---------------------------------------------
            bot_enabled=(settings.bot_enabled),
            backup_enabled=(settings.backup_enabled),
            proxy_enabled=(settings.proxy_enabled),
            retention_enabled=(settings.retention_enabled),
            database_healthy=(self._database_health.is_healthy()),
            scheduler_status=(self._get_scheduler_status()),
            uptime_seconds=(self._runtime.get_uptime_seconds()),
            # ---------------------------------------------
            # BACKUP
            # ---------------------------------------------
            latest_backup=(
                self._build_latest_backup(
                    latest_backup,
                    project_names=project_names,
                )
            ),
            # ---------------------------------------------
            # PROJECTS
            # ---------------------------------------------
            project_count=len(projects),
            enabled_project_count=(enabled_project_count),
            scheduled_project_count=(scheduled_project_count),
            admin_count=len(admins),
            # ---------------------------------------------
            # RUNTIME
            # ---------------------------------------------
            python_version=(platform.python_version()),
            operating_system=(platform.system() or "Unknown"),
            operating_system_version=(self._get_os_version()),
            architecture=(platform.machine() or "Unknown"),
            # ---------------------------------------------
            # CPU
            # ---------------------------------------------
            cpu_usage_percent=(
                psutil.cpu_percent(
                    interval=None,
                )
            ),
            cpu_physical_cores=(cpu_physical_cores),
            cpu_logical_cores=(cpu_logical_cores),
            # ---------------------------------------------
            # MEMORY
            # ---------------------------------------------
            memory_total_bytes=(memory.total),
            memory_used_bytes=(memory.used),
            memory_available_bytes=(memory.available),
            memory_usage_percent=(memory.percent),
            # ---------------------------------------------
            # DISK
            # ---------------------------------------------
            disk_total_bytes=(disk.total),
            disk_used_bytes=(disk.used),
            disk_free_bytes=(disk.free),
            disk_usage_percent=(disk.percent),
        )

    def _get_scheduler_status(
        self,
    ) -> SchedulerRuntimeStatus:
        """
        Resolve public scheduler runtime state.
        """

        if not self._scheduler.is_started:
            return SchedulerRuntimeStatus.STOPPED

        if self._scheduler.is_paused:
            return SchedulerRuntimeStatus.PAUSED

        return SchedulerRuntimeStatus.RUNNING

    @staticmethod
    def _build_latest_backup(
        history: BackupHistorySchema | None,
        *,
        project_names: dict[str, str],
    ) -> LatestBackupStatusSchema | None:
        """
        Convert latest backup history into a compact
        system-status representation.
        """

        if history is None:
            return None

        project_name = project_names.get(
            history.project_id,
            history.project_id,
        )

        return LatestBackupStatusSchema(
            history_id=history.id,
            project_id=history.project_id,
            project_name=project_name,
            status=history.status,
            archive_size_bytes=(history.archive_size_bytes),
            started_at=(history.started_at),
            finished_at=(history.finished_at),
            error_message=(history.error_message),
        )

    @staticmethod
    def _get_os_version() -> str:
        """
        Return a human-readable host operating-system version.
        """

        release = platform.release()

        version = platform.version()

        if release and version:
            return f"{release} ({version})"

        return release or version or "Unknown"

    @staticmethod
    def _get_disk_root() -> str:
        """
        Return filesystem root containing the application.
        """

        path = Path.cwd().resolve()

        return path.anchor or "/"


__all__ = [
    "SystemStatusService",
]
