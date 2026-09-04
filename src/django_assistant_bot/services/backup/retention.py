from __future__ import annotations

from dataclasses import (
    dataclass,
)
from pathlib import Path
from typing import Protocol

from django_assistant_bot.repositories.exceptions import (
    PersistenceError,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.services.backup.exceptions import (
    RetentionError,
)


class BackupHistoryRetentionRepository(Protocol):
    """
    Minimal persistence contract required
    by retention cleanup.
    """

    def list_successful_for_project(
        self,
        project_id: str,
    ) -> list[BackupHistorySchema]: ...

    def delete_by_id(
        self,
        history_id: str,
    ) -> bool: ...


@dataclass(
    frozen=True,
    slots=True,
)
class RetentionResult:
    """
    Result of one project retention cleanup.
    """

    removed_archives: tuple[
        Path,
        ...,
    ] = ()

    removed_history_ids: tuple[
        str,
        ...,
    ] = ()

    failed_archives: tuple[
        Path,
        ...,
    ] = ()


class RetentionService:
    """
    Apply backup retention consistently across
    archive files and backup history.

    Only successful backups participate in retention.

    Failed backup history is preserved for diagnostics.
    """

    def __init__(
        self,
        repository: BackupHistoryRetentionRepository,
    ) -> None:
        self._repository = repository

    def cleanup(
        self,
        *,
        project_id: str,
        keep_last: int,
    ) -> RetentionResult:
        """
        Keep only the newest successful backups.

        Archive deletion happens before history deletion.

        This intentionally avoids deleting the database
        record while leaving an unreachable archive file
        behind when filesystem deletion fails.
        """

        normalized_project_id = project_id.strip()

        if not normalized_project_id:
            raise RetentionError("Project ID cannot be empty.")

        if keep_last < 1:
            raise RetentionError(
                ("Retention keep_last must be " "greater than or equal to 1.")
            )

        try:
            histories = self._repository.list_successful_for_project(
                normalized_project_id
            )

        except PersistenceError as exc:
            raise RetentionError(
                ("Could not load backup history " "for retention.")
            ) from exc

        expired_histories = histories[keep_last:]

        removed_archives: list[Path] = []

        removed_history_ids: list[str] = []

        failed_archives: list[Path] = []

        for history in expired_histories:
            archive_path = history.archive_path

            if archive_path is not None:
                try:
                    if archive_path.exists():
                        archive_path.unlink()

                    removed_archives.append(archive_path)

                except OSError:
                    failed_archives.append(archive_path)

                    # Preserve history when its archive
                    # could not be removed.
                    continue

            try:
                deleted = self._repository.delete_by_id(history.id)

            except PersistenceError as exc:
                raise RetentionError(
                    (
                        "Archive cleanup completed "
                        "but backup history cleanup "
                        "failed."
                    )
                ) from exc

            if deleted:
                removed_history_ids.append(history.id)

        return RetentionResult(
            removed_archives=tuple(removed_archives),
            removed_history_ids=tuple(removed_history_ids),
            failed_archives=tuple(failed_archives),
        )


__all__ = [
    "BackupHistoryRetentionRepository",
    "RetentionResult",
    "RetentionService",
]
