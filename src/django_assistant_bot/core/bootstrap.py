from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import (
    Engine,
)
from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.core.environment import (
    EnvironmentManager,
    EnvironmentSettings,
)
from django_assistant_bot.database.engine import (
    create_database_engine,
)
from django_assistant_bot.database.session import (
    SessionManager,
)
from django_assistant_bot.repositories import (
    AdminRepository,
    AppSettingsRepository,
    BackupHistoryRepository,
    ProjectRepository,
)
from django_assistant_bot.services.admin import (
    AdminService,
)
from django_assistant_bot.services.backup import (
    BackupCoordinator,
    BackupHistoryService,
)
from django_assistant_bot.services.backup.retention import (
    RetentionService,
)
from django_assistant_bot.services.database_health import (
    DatabaseHealthService,
)
from django_assistant_bot.services.project import (
    ProjectService,
)
from django_assistant_bot.services.runtime import (
    ApplicationRuntimeService,
)
from django_assistant_bot.services.scheduler import (
    BackupSchedulerService,
)
from django_assistant_bot.services.settings import (
    AppSettingsService,
)
from django_assistant_bot.services.system_status import (
    SystemStatusService,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ApplicationBootstrap:
    """
    Fully initialized application dependency graph.
    """

    environment: EnvironmentSettings

    engine: Engine

    context: ApplicationContext


def bootstrap_application() -> ApplicationBootstrap:
    """
    Initialize application infrastructure and services.

    Dependency flow:

        Environment
            ↓
        SQLAlchemy Engine
            ↓
        SessionManager
            ↓
        Repositories
            ↓
        Services
            ↓
        BackupCoordinator
            ↓
        ApplicationContext
    """

    # -----------------------------------------------------
    # ENVIRONMENT
    # -----------------------------------------------------

    environment = EnvironmentManager().load()

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    engine = create_database_engine()

    sessions = SessionManager(
        engine,
    )

    # -----------------------------------------------------
    # REPOSITORIES
    # -----------------------------------------------------

    project_repository = ProjectRepository(
        sessions,
    )

    admin_repository = AdminRepository(
        sessions,
    )

    settings_repository = AppSettingsRepository(
        sessions,
    )

    backup_history_repository = BackupHistoryRepository(
        sessions,
    )

    # -----------------------------------------------------
    # SERVICES
    # -----------------------------------------------------

    project_service = ProjectService(
        project_repository,
    )

    admin_service = AdminService(
        admin_repository,
    )

    settings_service = AppSettingsService(
        settings_repository,
    )

    backup_history_service = BackupHistoryService(
        backup_history_repository,
    )

    runtime_service = ApplicationRuntimeService()

    database_health_service = DatabaseHealthService(
        sessions,
    )

    retention_service = RetentionService(
        backup_history_repository,
    )

    # -----------------------------------------------------
    # BACKUP ORCHESTRATION
    # -----------------------------------------------------

    backup_coordinator = BackupCoordinator(
        projects=project_service,
        settings=settings_service,
        history=backup_history_repository,
        retention=retention_service,
    )

    # -----------------------------------------------------
    # SCHEDULER
    # -----------------------------------------------------

    backup_scheduler = BackupSchedulerService(
        projects=(project_service),
        backups=(backup_coordinator),
    )

    # -----------------------------------------------------
    # SYSTEM STATUS
    # -----------------------------------------------------

    system_status_service = SystemStatusService(
        settings=(settings_service),
        projects=(project_service),
        admins=(admin_service),
        scheduler=(backup_scheduler),
        runtime=(runtime_service),
        database_health=(database_health_service),
        backup_history=(backup_history_service),
    )

    # -----------------------------------------------------
    # BOOTSTRAP ADMINS
    # -----------------------------------------------------

    _bootstrap_admins(
        admin_service=(admin_service),
        environment=(environment),
    )

    # -----------------------------------------------------
    # APPLICATION CONTEXT
    # -----------------------------------------------------

    context = ApplicationContext(
        environment=(environment),
        projects=(project_service),
        admins=(admin_service),
        settings=(settings_service),
        backups=(backup_coordinator),
        backup_history=(backup_history_service),
        scheduler=(backup_scheduler),
        system_status=(system_status_service),
    )

    return ApplicationBootstrap(
        environment=environment,
        engine=engine,
        context=context,
    )


def _bootstrap_admins(
    *,
    admin_service: AdminService,
    environment: EnvironmentSettings,
) -> None:
    """
    Ensure bootstrap administrators exist.

    This enables first-time access before Telegram-based
    administrator management is available.
    """

    for telegram_user_id in environment.bootstrap_admin_ids:
        if admin_service.is_admin(
            telegram_user_id,
        ):
            continue

        admin_service.add_admin(
            telegram_user_id,
        )


__all__ = [
    "ApplicationBootstrap",
    "bootstrap_application",
]
