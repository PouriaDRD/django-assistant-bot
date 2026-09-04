from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    select,
)
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from django_assistant_bot.database.models.project import (
    ProjectModel,
)
from django_assistant_bot.database.session import (
    SessionManager,
)
from django_assistant_bot.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    PersistenceError,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectCreateSchema,
    ProjectSchema,
    ProjectUpdateSchema,
    ScheduleSchema,
    ScheduleUpdateSchema,
)


class ProjectRepository:
    """
    Persistence gateway for projects.

    SQLAlchemy models never leave this repository.
    """

    def __init__(
        self,
        sessions: SessionManager,
    ) -> None:
        self._sessions = sessions

    def list_all(
        self,
    ) -> list[ProjectSchema]:
        try:
            with self._sessions.session() as session:
                statement = select(ProjectModel).order_by(ProjectModel.created_at.asc())

                models = list(session.scalars(statement))

                return [self._to_schema(model) for model in models]

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load projects.") from exc

    def get_by_id(
        self,
        project_id: str,
    ) -> ProjectSchema | None:
        try:
            with self._sessions.session() as session:
                model = session.get(
                    ProjectModel,
                    project_id,
                )

                if model is None:
                    return None

                return self._to_schema(model)

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load project.") from exc

    def get_by_name(
        self,
        name: str,
    ) -> ProjectSchema | None:
        normalized = name.strip()

        try:
            with self._sessions.session() as session:
                statement = select(ProjectModel).where(ProjectModel.name == normalized)

                model = session.scalar(statement)

                if model is None:
                    return None

                return self._to_schema(model)

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load project.") from exc

    def exists_by_name(
        self,
        name: str,
    ) -> bool:
        return self.get_by_name(name) is not None

    def create(
        self,
        data: ProjectCreateSchema,
    ) -> ProjectSchema:
        model = ProjectModel(
            name=data.name,
            enabled=True,
            database_type=data.database.type,
            database_path=str(data.database.path),
            media_enabled=data.media.enabled,
            media_path=str(data.media.path),
            schedule_enabled=(data.schedule.enabled),
            schedule_interval=(data.schedule.interval),
            schedule_unit=(data.schedule.unit),
        )

        try:
            with self._sessions.transaction() as session:
                session.add(model)

                session.flush()

                project = self._to_schema(model)

            return project

        except IntegrityError as exc:
            raise DuplicateEntityError(f"Project already exists: {data.name}") from exc

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not create project.") from exc

    def update(
        self,
        project_id: str,
        data: ProjectUpdateSchema,
    ) -> ProjectSchema:
        try:
            with self._sessions.transaction() as session:
                model = session.get(
                    ProjectModel,
                    project_id,
                )

                if model is None:
                    raise EntityNotFoundError(f"Project not found: {project_id}")

                if data.name is not None:
                    model.name = data.name

                if data.enabled is not None:
                    model.enabled = data.enabled

                if data.database is not None:
                    model.database_type = data.database.type

                    model.database_path = str(data.database.path)

                if data.media is not None:
                    model.media_enabled = data.media.enabled

                    model.media_path = str(data.media.path)

                if data.schedule is not None:
                    model.schedule_enabled = data.schedule.enabled

                    model.schedule_interval = data.schedule.interval

                    model.schedule_unit = data.schedule.unit

                session.flush()

                project = self._to_schema(model)

            return project

        except (
            EntityNotFoundError,
            DuplicateEntityError,
        ):
            raise

        except IntegrityError as exc:
            raise DuplicateEntityError("Project name already exists.") from exc

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not update project.") from exc

    def update_schedule(
        self,
        project_id: str,
        data: ScheduleUpdateSchema,
    ) -> ProjectSchema:
        """
        Partially update project backup schedule.

        Fields with a value of None remain unchanged.
        """

        try:
            with self._sessions.transaction() as session:
                model = session.get(
                    ProjectModel,
                    project_id,
                )

                if model is None:
                    raise EntityNotFoundError(f"Project not found: {project_id}")

                if data.enabled is not None:
                    model.schedule_enabled = data.enabled

                if data.interval is not None:
                    model.schedule_interval = data.interval

                if data.unit is not None:
                    model.schedule_unit = data.unit

                session.flush()

                project = self._to_schema(model)

            return project

        except EntityNotFoundError:
            raise

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not update project schedule.") from exc

    def set_enabled(
        self,
        project_id: str,
        enabled: bool,
    ) -> ProjectSchema:
        return self.update(
            project_id,
            ProjectUpdateSchema(
                enabled=enabled,
            ),
        )

    def delete(
        self,
        project_id: str,
    ) -> ProjectSchema:
        try:
            with self._sessions.transaction() as session:
                model = session.get(
                    ProjectModel,
                    project_id,
                )

                if model is None:
                    raise EntityNotFoundError(f"Project not found: {project_id}")

                project = self._to_schema(model)

                session.delete(model)

            return project

        except EntityNotFoundError:
            raise

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not delete project.") from exc

    @staticmethod
    def _to_schema(
        model: ProjectModel,
    ) -> ProjectSchema:
        return ProjectSchema(
            id=model.id,
            name=model.name,
            enabled=model.enabled,
            database=DatabaseSchema(
                type=model.database_type,
                path=Path(model.database_path),
            ),
            media=MediaSchema(
                enabled=model.media_enabled,
                path=Path(model.media_path),
            ),
            schedule=ScheduleSchema(
                enabled=(model.schedule_enabled),
                interval=(model.schedule_interval),
                unit=model.schedule_unit,
            ),
        )
