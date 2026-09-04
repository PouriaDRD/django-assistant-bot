from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.admin import (
    AdminSchema,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)
from django_assistant_bot.schemas.system_status import (
    SchedulerRuntimeStatus,
)
from django_assistant_bot.services.system_status import (
    SystemStatusService,
)

# =========================================================
# BUILDERS
# =========================================================


def build_settings(
    *,
    bot_enabled: bool = True,
    backup_enabled: bool = True,
    proxy_enabled: bool = False,
    retention_enabled: bool = True,
) -> AppSettingsSchema:
    """
    Build application settings for system status tests.
    """

    return AppSettingsSchema(
        bot_enabled=bot_enabled,
        backup_enabled=backup_enabled,
        backup_directory=Path("./backups"),
        compression_level=6,
        retention_enabled=(retention_enabled),
        retention_keep_last=10,
        proxy_enabled=(proxy_enabled),
        proxy_url="",
    )


def build_admin(
    telegram_user_id: int,
) -> AdminSchema:
    """
    Build administrator schema for tests.
    """

    return AdminSchema(
        created_at=datetime.now(),
        telegram_user_id=(telegram_user_id),
    )


def build_project(
    *,
    project_id: str,
    enabled: bool = True,
    schedule_enabled: bool = True,
) -> ProjectSchema:
    """
    Build project schema for system status tests.
    """

    return ProjectSchema(
        id=project_id,
        name=(f"Project {project_id}"),
        enabled=enabled,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=Path(f"/projects/{project_id}/db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=True,
            path=Path(f"/projects/{project_id}/media"),
        ),
        schedule=ScheduleSchema(
            enabled=(schedule_enabled),
            interval=1,
            unit=(ScheduleUnit.MINUTES),
        ),
    )


def build_runtime(
    *,
    uptime_seconds: float = 3600.0,
) -> Mock:
    """
    Build application runtime mock.
    """

    runtime = Mock()

    runtime.get_uptime_seconds.return_value = uptime_seconds

    return runtime


def build_database_health(
    *,
    healthy: bool = True,
) -> Mock:
    """
    Build database health mock.
    """

    database_health = Mock()

    database_health.is_healthy.return_value = healthy

    return database_health


def build_service(
    *,
    settings: Mock,
    projects: Mock,
    admins: Mock,
    scheduler: Mock,
    runtime: Mock | None = None,
    database_health: Mock | None = None,
) -> SystemStatusService:
    """
    Build system status service with mocked dependencies.
    """

    return SystemStatusService(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
        runtime=(runtime or build_runtime()),
        database_health=(database_health or build_database_health()),
    )


# =========================================================
# SNAPSHOT
# =========================================================


def test_get_status_returns_runtime_snapshot() -> None:
    settings = Mock()

    settings.get_settings.return_value = build_settings(
        bot_enabled=True,
        backup_enabled=True,
        proxy_enabled=False,
        retention_enabled=True,
    )

    projects = Mock()

    projects.list_projects.return_value = [
        build_project(
            project_id="1",
            enabled=True,
            schedule_enabled=True,
        ),
        build_project(
            project_id="2",
            enabled=True,
            schedule_enabled=False,
        ),
        build_project(
            project_id="3",
            enabled=False,
            schedule_enabled=True,
        ),
    ]

    admins = Mock()

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
        build_admin(
            222,
        ),
    ]

    scheduler = Mock()

    scheduler.is_started = True

    scheduler.is_paused = False

    runtime = build_runtime(
        uptime_seconds=7200.5,
    )

    database_health = build_database_health(
        healthy=True,
    )

    service = build_service(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
        runtime=runtime,
        database_health=database_health,
    )

    result = service.get_status()

    assert result.bot_enabled is True

    assert result.backup_enabled is True

    assert result.proxy_enabled is False

    assert result.retention_enabled is True

    assert result.database_healthy is True

    assert result.uptime_seconds == 7200.5

    assert result.scheduler_status == SchedulerRuntimeStatus.RUNNING

    assert result.project_count == 3

    assert result.enabled_project_count == 2

    assert result.scheduled_project_count == 1

    assert result.admin_count == 2

    assert result.python_version

    assert result.operating_system

    runtime.get_uptime_seconds.assert_called_once_with()

    database_health.is_healthy.assert_called_once_with()


# =========================================================
# SCHEDULER STATUS
# =========================================================


@pytest.mark.parametrize(
    (
        "is_started",
        "is_paused",
        "expected",
    ),
    [
        (
            False,
            False,
            SchedulerRuntimeStatus.STOPPED,
        ),
        (
            True,
            False,
            SchedulerRuntimeStatus.RUNNING,
        ),
        (
            True,
            True,
            SchedulerRuntimeStatus.PAUSED,
        ),
    ],
)
def test_scheduler_status(
    is_started: bool,
    is_paused: bool,
    expected: SchedulerRuntimeStatus,
) -> None:
    settings = Mock()

    settings.get_settings.return_value = build_settings()

    projects = Mock()

    projects.list_projects.return_value = []

    admins = Mock()

    admins.list_admins.return_value = []

    scheduler = Mock()

    scheduler.is_started = is_started

    scheduler.is_paused = is_paused

    service = build_service(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
    )

    result = service.get_status()

    assert result.scheduler_status == expected


# =========================================================
# DATABASE HEALTH
# =========================================================


def test_database_health_is_exposed() -> None:
    settings = Mock()

    settings.get_settings.return_value = build_settings()

    projects = Mock()

    projects.list_projects.return_value = []

    admins = Mock()

    admins.list_admins.return_value = []

    scheduler = Mock()

    scheduler.is_started = True

    scheduler.is_paused = False

    database_health = build_database_health(
        healthy=False,
    )

    service = build_service(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
        database_health=database_health,
    )

    result = service.get_status()

    assert result.database_healthy is False


# =========================================================
# UPTIME
# =========================================================


def test_uptime_is_exposed() -> None:
    settings = Mock()

    settings.get_settings.return_value = build_settings()

    projects = Mock()

    projects.list_projects.return_value = []

    admins = Mock()

    admins.list_admins.return_value = []

    scheduler = Mock()

    scheduler.is_started = True

    scheduler.is_paused = False

    runtime = build_runtime(
        uptime_seconds=123.5,
    )

    service = build_service(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
        runtime=runtime,
    )

    result = service.get_status()

    assert result.uptime_seconds == 123.5


# =========================================================
# PROJECT COUNTS
# =========================================================


def test_disabled_project_is_not_counted_as_scheduled() -> None:
    settings = Mock()

    settings.get_settings.return_value = build_settings()

    projects = Mock()

    projects.list_projects.return_value = [
        build_project(
            project_id="1",
            enabled=False,
            schedule_enabled=True,
        ),
    ]

    admins = Mock()

    admins.list_admins.return_value = []

    scheduler = Mock()

    scheduler.is_started = True

    scheduler.is_paused = False

    service = build_service(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
    )

    result = service.get_status()

    assert result.project_count == 1

    assert result.enabled_project_count == 0

    assert result.scheduled_project_count == 0


def test_schedule_disabled_project_is_not_counted_as_scheduled() -> None:
    settings = Mock()

    settings.get_settings.return_value = build_settings()

    projects = Mock()

    projects.list_projects.return_value = [
        build_project(
            project_id="1",
            enabled=True,
            schedule_enabled=False,
        ),
    ]

    admins = Mock()

    admins.list_admins.return_value = []

    scheduler = Mock()

    scheduler.is_started = True

    scheduler.is_paused = False

    service = build_service(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
    )

    result = service.get_status()

    assert result.project_count == 1

    assert result.enabled_project_count == 1

    assert result.scheduled_project_count == 0


def test_empty_application_returns_zero_counts() -> None:
    settings = Mock()

    settings.get_settings.return_value = build_settings()

    projects = Mock()

    projects.list_projects.return_value = []

    admins = Mock()

    admins.list_admins.return_value = []

    scheduler = Mock()

    scheduler.is_started = True

    scheduler.is_paused = False

    service = build_service(
        settings=settings,
        projects=projects,
        admins=admins,
        scheduler=scheduler,
    )

    result = service.get_status()

    assert result.project_count == 0

    assert result.enabled_project_count == 0

    assert result.scheduled_project_count == 0

    assert result.admin_count == 0
