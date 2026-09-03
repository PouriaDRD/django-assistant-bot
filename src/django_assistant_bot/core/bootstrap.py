from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from django_assistant_bot.bot.context import ApplicationContext
from django_assistant_bot.core.environment import (
    EnvironmentManager,
    EnvironmentSettings,
)
from django_assistant_bot.database.engine import create_database_engine
from django_assistant_bot.database.session import SessionManager
from django_assistant_bot.repositories import (
    AdminRepository,
    AppSettingsRepository,
    ProjectRepository,
)
from django_assistant_bot.services.admin import AdminService
from django_assistant_bot.services.project import ProjectService
from django_assistant_bot.services.settings import AppSettingsService


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
        ApplicationContext
    """

    environment = EnvironmentManager().load()

    engine = create_database_engine(
        environment,
    )

    sessions = SessionManager(
        engine,
    )

    project_repository = ProjectRepository(
        sessions,
    )

    admin_repository = AdminRepository(
        sessions,
    )

    settings_repository = AppSettingsRepository(
        sessions,
    )

    project_service = ProjectService(
        project_repository,
    )

    admin_service = AdminService(
        admin_repository,
    )

    settings_service = AppSettingsService(
        settings_repository,
    )

    _bootstrap_admins(
        admin_service=admin_service,
        environment=environment,
    )

    context = ApplicationContext(
        environment=environment,
        projects=project_service,
        admins=admin_service,
        settings=settings_service,
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
