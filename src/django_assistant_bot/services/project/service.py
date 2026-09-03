from __future__ import annotations

from django_assistant_bot.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    PersistenceError,
)
from django_assistant_bot.repositories.project import ProjectRepository
from django_assistant_bot.schemas.project import (
    ProjectCreateSchema,
    ProjectSchema,
    ProjectUpdateSchema,
)
from django_assistant_bot.services.project.exceptions import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    ProjectPersistenceError,
    ProjectValidationError,
)


class ProjectService:
    """
    Application service responsible for project business logic.

    The service does not know anything about:
    - SQLAlchemy sessions
    - SQLite
    - Telegram
    - Flask
    - JSON configuration
    """

    def __init__(
        self,
        repository: ProjectRepository,
    ) -> None:
        self._repository = repository

    def list_projects(self) -> list[ProjectSchema]:
        try:
            return self._repository.list_all()

        except PersistenceError as exc:
            raise ProjectPersistenceError("Could not load projects.") from exc

    def get_project(
        self,
        project_id: str,
    ) -> ProjectSchema:
        normalized_id = project_id.strip()

        if not normalized_id:
            raise ProjectValidationError("Project ID cannot be empty.")

        try:
            project = self._repository.get_by_id(
                normalized_id,
            )

        except PersistenceError as exc:
            raise ProjectPersistenceError("Could not load project.") from exc

        if project is None:
            raise ProjectNotFoundError(f"Project not found: {normalized_id}")

        return project

    def create_project(
        self,
        data: ProjectCreateSchema,
    ) -> ProjectSchema:
        self._validate_create_data(data)

        try:
            return self._repository.create(data)

        except DuplicateEntityError as exc:
            raise ProjectAlreadyExistsError(
                f"Project already exists: {data.name}"
            ) from exc

        except PersistenceError as exc:
            raise ProjectPersistenceError("Could not create project.") from exc

    def update_project(
        self,
        project_id: str,
        data: ProjectUpdateSchema,
    ) -> ProjectSchema:
        normalized_id = project_id.strip()

        if not normalized_id:
            raise ProjectValidationError("Project ID cannot be empty.")

        self._validate_update_data(data)

        try:
            return self._repository.update(
                normalized_id,
                data,
            )

        except EntityNotFoundError as exc:
            raise ProjectNotFoundError(f"Project not found: {normalized_id}") from exc

        except DuplicateEntityError as exc:
            raise ProjectAlreadyExistsError(
                "A project with this name already exists."
            ) from exc

        except PersistenceError as exc:
            raise ProjectPersistenceError("Could not update project.") from exc

    def set_enabled(
        self,
        project_id: str,
        enabled: bool,
    ) -> ProjectSchema:
        normalized_id = project_id.strip()

        if not normalized_id:
            raise ProjectValidationError("Project ID cannot be empty.")

        try:
            return self._repository.set_enabled(
                normalized_id,
                enabled,
            )

        except EntityNotFoundError as exc:
            raise ProjectNotFoundError(f"Project not found: {normalized_id}") from exc

        except PersistenceError as exc:
            raise ProjectPersistenceError("Could not update project status.") from exc

    def delete_project(
        self,
        project_id: str,
    ) -> ProjectSchema:
        normalized_id = project_id.strip()

        if not normalized_id:
            raise ProjectValidationError("Project ID cannot be empty.")

        try:
            return self._repository.delete(
                normalized_id,
            )

        except EntityNotFoundError as exc:
            raise ProjectNotFoundError(f"Project not found: {normalized_id}") from exc

        except PersistenceError as exc:
            raise ProjectPersistenceError("Could not delete project.") from exc

    @staticmethod
    def _validate_create_data(
        data: ProjectCreateSchema,
    ) -> None:
        if not data.database.path.is_absolute():
            raise ProjectValidationError("Database path must be absolute.")

        if not data.media.path.is_absolute():
            raise ProjectValidationError("Media path must be absolute.")

    @staticmethod
    def _validate_update_data(
        data: ProjectUpdateSchema,
    ) -> None:
        if data.database is not None and not data.database.path.is_absolute():
            raise ProjectValidationError("Database path must be absolute.")

        if data.media is not None and not data.media.path.is_absolute():
            raise ProjectValidationError("Media path must be absolute.")
