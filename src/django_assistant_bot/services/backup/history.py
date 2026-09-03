from __future__ import annotations

from django_assistant_bot.repositories.backup_history import (
    BackupHistoryRepository,
)
from django_assistant_bot.repositories.exceptions import (
    PersistenceError,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.services.backup.history_exceptions import (
    BackupHistoryNotFoundError,
    BackupHistoryPersistenceError,
    BackupHistoryValidationError,
)


class BackupHistoryService:
    """
    Read-only application service for backup history.
    """

    def __init__(
        self,
        repository: BackupHistoryRepository,
    ) -> None:
        self._repository = repository

    # -----------------------------------------------------
    # LIST
    # -----------------------------------------------------

    def list_for_project(
        self,
        project_id: str,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> list[BackupHistorySchema]:
        """
        Return backup history for a project.
        """

        normalized_project_id = project_id.strip()

        if not normalized_project_id:
            raise BackupHistoryValidationError("Project ID cannot be empty.")

        if limit < 1:
            raise BackupHistoryValidationError("Limit must be greater than zero.")

        if offset < 0:
            raise BackupHistoryValidationError("Offset cannot be negative.")

        try:
            return self._repository.list_for_project(
                normalized_project_id,
                limit=limit,
                offset=offset,
            )

        except PersistenceError as exc:
            raise BackupHistoryPersistenceError(
                "Could not load backup history."
            ) from exc

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    def get_history(
        self,
        history_id: str,
        *,
        project_id: str | None = None,
    ) -> BackupHistorySchema:
        """
        Return a single backup history record.

        When project_id is supplied, the record must belong
        to that project.
        """

        normalized_history_id = history_id.strip()

        if not normalized_history_id:
            raise BackupHistoryValidationError("History ID cannot be empty.")

        try:
            history = self._repository.get_by_id(
                normalized_history_id,
            )

        except PersistenceError as exc:
            raise BackupHistoryPersistenceError(
                "Could not load backup history."
            ) from exc

        if history is None:
            raise BackupHistoryNotFoundError("Backup history was not found.")

        if project_id is not None:
            normalized_project_id = project_id.strip()

            if not normalized_project_id:
                raise BackupHistoryValidationError("Project ID cannot be empty.")

            if history.project_id != normalized_project_id:
                raise BackupHistoryNotFoundError(
                    "Backup history was not found " "for this project."
                )

        return history
