from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from config.models import (
    AppConfig,
    DatabaseConfig,
    MediaConfig,
    ProjectConfig,
    ScheduleConfig,
)
from config.settings_manager import SettingsManager
from config.exceptions import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    ProjectValidationError,
)


@dataclass(frozen=True, slots=True)
class ProjectCreateData:
    name: str
    database_path: Path
    media_path: Path
    schedule: ScheduleConfig


class ProjectService:
    """
    Handles project lifecycle and configuration mutations.
    """

    def __init__(
        self,
        settings: SettingsManager,
    ) -> None:
        self._settings = settings

    def list_projects(self) -> list[ProjectConfig]:
        config = self._settings.load()

        return list(config.projects)

    def get_project(
        self,
        project_id: str,
    ) -> ProjectConfig:
        config = self._settings.load()

        for project in config.projects:
            if project.id == project_id:
                return project

        raise ProjectNotFoundError(f"Project not found: {project_id}")

    def create_project(
        self,
        data: ProjectCreateData,
    ) -> ProjectConfig:
        config = self._settings.load()

        normalized_name = data.name.strip()

        if not normalized_name:
            raise ProjectValidationError("Project name cannot be empty.")

        if not data.database_path.is_absolute():
            raise ProjectValidationError("Database path must be absolute.")

        if not data.media_path.is_absolute():
            raise ProjectValidationError("Media path must be absolute.")

        if any(
            project.name.casefold() == normalized_name.casefold()
            for project in config.projects
        ):
            raise ProjectAlreadyExistsError(
                f"Project already exists: {normalized_name}"
            )

        project = ProjectConfig(
            id=self._generate_project_id(),
            name=normalized_name,
            database=DatabaseConfig(
                path=data.database_path,
            ),
            media=MediaConfig(
                path=data.media_path,
            ),
            schedule=data.schedule,
        )

        new_config = config.model_copy(
            update={
                "projects": [
                    *config.projects,
                    project,
                ],
            },
        )

        self._settings.save(new_config)

        return project

    def delete_project(
        self,
        project_id: str,
    ) -> ProjectConfig:
        config = self._settings.load()

        project = self._find_project(
            config,
            project_id,
        )

        new_config = config.model_copy(
            update={
                "projects": [item for item in config.projects if item.id != project_id],
            },
        )

        self._settings.save(new_config)

        return project

    def set_enabled(
        self,
        project_id: str,
        enabled: bool,
    ) -> ProjectConfig:
        config = self._settings.load()

        project = self._find_project(
            config,
            project_id,
        )

        updated_project = project.model_copy(
            update={
                "enabled": enabled,
            },
        )

        new_projects = [
            updated_project if item.id == project_id else item
            for item in config.projects
        ]

        new_config = config.model_copy(
            update={
                "projects": new_projects,
            },
        )

        self._settings.save(new_config)

        return updated_project

    @staticmethod
    def _find_project(
        config: AppConfig,
        project_id: str,
    ) -> ProjectConfig:
        for project in config.projects:
            if project.id == project_id:
                return project

        raise ProjectNotFoundError(f"Project not found: {project_id}")

    @staticmethod
    def _generate_project_id() -> str:
        return uuid4().hex
