from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    select,
)
from sqlalchemy.exc import (
    SQLAlchemyError,
)

from django_assistant_bot.database.models.backup_history import (
    BackupHistoryModel,
)
from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.database.session import (
    SessionManager,
)
from django_assistant_bot.repositories.exceptions import (
    PersistenceError,
)
from django_assistant_bot.schemas.backup import (
    BackupHistoryCreateSchema,
    BackupHistorySchema,
)


class BackupHistoryRepository:
    """
    Persistence layer for backup history records.
    """

    def __init__(
        self,
        sessions: SessionManager,
    ) -> None:
        self._sessions = sessions

    # =====================================================
    # CREATE
    # =====================================================

    def create(
        self,
        data: BackupHistoryCreateSchema,
    ) -> BackupHistorySchema:
        """
        Create and persist a backup history record.
        """

        model = BackupHistoryModel(
            project_id=data.project_id,
            status=data.status,
            archive_path=(
                str(data.archive_path) if data.archive_path is not None else None
            ),
            database_size_bytes=(data.database_size_bytes),
            media_size_bytes=(data.media_size_bytes),
            archive_size_bytes=(data.archive_size_bytes),
            media_file_count=(data.media_file_count),
            checksum_algorithm=(data.checksum_algorithm),
            checksum_value=(data.checksum_value),
            error_message=(data.error_message),
            started_at=data.started_at,
            finished_at=data.finished_at,
        )

        try:
            with self._sessions.transaction() as session:
                session.add(
                    model,
                )

                session.flush()

                history = self._to_schema(
                    model,
                )

            return history

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not create backup history.") from exc

    # =====================================================
    # GET
    # =====================================================

    def get_by_id(
        self,
        history_id: str,
    ) -> BackupHistorySchema | None:
        """
        Return a backup history record by ID.
        """

        try:
            with self._sessions.session() as session:
                statement = select(BackupHistoryModel).where(
                    BackupHistoryModel.id == history_id
                )

                model = session.scalars(statement).first()

                if model is None:
                    return None

                return self._to_schema(
                    model,
                )

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load backup history.") from exc

    def get_latest(
        self,
    ) -> BackupHistorySchema | None:
        """
        Return the newest backup history record.

        Records are ordered by backup start time
        descending.
        """

        try:
            with self._sessions.session() as session:
                statement = (
                    select(BackupHistoryModel)
                    .order_by(BackupHistoryModel.started_at.desc())
                    .limit(1)
                )

                model = session.scalars(statement).first()

                if model is None:
                    return None

                return self._to_schema(
                    model,
                )

        except SQLAlchemyError as exc:
            raise PersistenceError(
                ("Could not load latest " "backup history.")
            ) from exc

    # =====================================================
    # LIST
    # =====================================================

    def list_all(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BackupHistorySchema]:
        """
        Return backup history for all projects.

        Records are ordered newest first.
        """

        safe_limit = max(
            1,
            min(
                limit,
                500,
            ),
        )

        safe_offset = max(
            0,
            offset,
        )

        try:
            with self._sessions.session() as session:
                statement = (
                    select(BackupHistoryModel)
                    .order_by(BackupHistoryModel.started_at.desc())
                    .offset(safe_offset)
                    .limit(safe_limit)
                )

                models = list(session.scalars(statement))

                return [
                    self._to_schema(
                        model,
                    )
                    for model in models
                ]

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load backup history.") from exc

    def list_for_project(
        self,
        project_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BackupHistorySchema]:
        """
        Return project backup history ordered
        newest first.
        """

        safe_limit = max(
            1,
            min(
                limit,
                500,
            ),
        )

        safe_offset = max(
            0,
            offset,
        )

        try:
            with self._sessions.session() as session:
                statement = (
                    select(BackupHistoryModel)
                    .where(BackupHistoryModel.project_id == project_id)
                    .order_by(BackupHistoryModel.started_at.desc())
                    .offset(safe_offset)
                    .limit(safe_limit)
                )

                models = list(session.scalars(statement))

                return [
                    self._to_schema(
                        model,
                    )
                    for model in models
                ]

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load backup history.") from exc

    # =====================================================
    # RETENTION
    # =====================================================

    def list_successful_for_project(
        self,
        project_id: str,
    ) -> list[BackupHistorySchema]:
        """
        Return successful project backup history
        ordered newest first.

        This query is used by retention cleanup.
        """

        try:
            with self._sessions.session() as session:
                statement = (
                    select(BackupHistoryModel)
                    .where(
                        BackupHistoryModel.project_id == project_id,
                        BackupHistoryModel.status == BackupStatus.SUCCESS,
                    )
                    .order_by(BackupHistoryModel.started_at.desc())
                )

                models = list(session.scalars(statement))

                return [
                    self._to_schema(
                        model,
                    )
                    for model in models
                ]

        except SQLAlchemyError as exc:
            raise PersistenceError(
                ("Could not load successful " "backup history.")
            ) from exc

    def delete_by_id(
        self,
        history_id: str,
    ) -> bool:
        """
        Delete one backup history record.

        Returns True when a record was deleted.
        """

        try:
            with self._sessions.transaction() as session:
                statement = select(BackupHistoryModel).where(
                    BackupHistoryModel.id == history_id
                )

                model = session.scalars(statement).first()

                if model is None:
                    return False

                session.delete(model)

                return True

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not delete backup history.") from exc

    # =====================================================
    # MAPPING
    # =====================================================

    @staticmethod
    def _to_schema(
        model: BackupHistoryModel,
    ) -> BackupHistorySchema:
        """
        Convert persistence model into public schema.
        """

        return BackupHistorySchema(
            id=model.id,
            project_id=model.project_id,
            status=model.status,
            archive_path=(
                Path(model.archive_path) if model.archive_path is not None else None
            ),
            database_size_bytes=(model.database_size_bytes),
            media_size_bytes=(model.media_size_bytes),
            archive_size_bytes=(model.archive_size_bytes),
            media_file_count=(model.media_file_count),
            checksum_algorithm=(model.checksum_algorithm),
            checksum_value=(model.checksum_value),
            error_message=(model.error_message),
            started_at=(model.started_at),
            finished_at=(model.finished_at),
        )


__all__ = [
    "BackupHistoryRepository",
]
