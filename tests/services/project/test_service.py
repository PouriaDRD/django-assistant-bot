from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.database.session import (
    SessionManager,
)
from django_assistant_bot.repositories.project import (
    ProjectRepository,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectCreateSchema,
    ProjectUpdateSchema,
    ScheduleSchema,
    ScheduleUpdateSchema,
)
from django_assistant_bot.services.project import (
    ProjectAlreadyExistsError,
    ProjectNotFoundError,
    ProjectService,
    ProjectValidationError,
)

# =========================================================
# FIXTURES
# =========================================================


@pytest.fixture()
def service(
    session_manager: SessionManager,
) -> ProjectService:
    repository = ProjectRepository(
        session_manager,
    )

    return ProjectService(
        repository,
    )


@pytest.fixture()
def project_data(
    tmp_path: Path,
) -> ProjectCreateSchema:
    """
    Build valid project data backed by real temporary
    filesystem paths.

    ProjectService validates that:
    - database exists and is a file
    - enabled media exists and is a directory
    """

    database_path = tmp_path / "db.sqlite3"

    database_path.write_bytes(b"sqlite-test")

    media_path = tmp_path / "media"

    media_path.mkdir()

    return ProjectCreateSchema(
        name="service-test",
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=database_path,
        ),
        media=MediaSchema(
            enabled=True,
            path=media_path,
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=30,
            unit=ScheduleUnit.MINUTES,
        ),
    )


# =========================================================
# CREATE
# =========================================================


def test_create_project(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    assert project.id

    assert project.name == "service-test"

    assert project.enabled is True

    assert project.database.type is DatabaseType.SQLITE

    assert project.database.path == project_data.database.path

    assert project.media.path == project_data.media.path

    assert project.schedule.interval == 30

    assert project.schedule.unit is ScheduleUnit.MINUTES


def test_create_duplicate_project_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    service.create_project(
        project_data,
    )

    with pytest.raises(
        ProjectAlreadyExistsError,
    ):
        service.create_project(
            project_data,
        )


def test_create_duplicate_project_name_is_case_insensitive(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    service.create_project(
        project_data,
    )

    duplicate = project_data.model_copy(
        update={
            "name": "SERVICE-TEST",
        },
    )

    with pytest.raises(
        ProjectAlreadyExistsError,
    ):
        service.create_project(
            duplicate,
        )


# =========================================================
# CREATE PATH VALIDATION
# =========================================================


def test_create_project_with_relative_database_path_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    invalid = project_data.model_copy(
        update={
            "database": DatabaseSchema(
                type=DatabaseType.SQLITE,
                path=Path("relative/db.sqlite3"),
            ),
        },
    )

    with pytest.raises(
        ProjectValidationError,
        match="Database path must be absolute",
    ):
        service.create_project(
            invalid,
        )


def test_create_project_with_missing_database_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    invalid = project_data.model_copy(
        update={
            "database": DatabaseSchema(
                type=DatabaseType.SQLITE,
                path=(tmp_path / "missing.sqlite3"),
            ),
        },
    )

    with pytest.raises(
        ProjectValidationError,
        match="Database file does not exist",
    ):
        service.create_project(
            invalid,
        )


def test_create_project_with_database_directory_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    database_directory = tmp_path / "database-directory"

    database_directory.mkdir()

    invalid = project_data.model_copy(
        update={
            "database": DatabaseSchema(
                type=DatabaseType.SQLITE,
                path=database_directory,
            ),
        },
    )

    with pytest.raises(
        ProjectValidationError,
        match=("Database path must point to a file"),
    ):
        service.create_project(
            invalid,
        )


def test_create_project_with_relative_media_path_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    invalid = project_data.model_copy(
        update={
            "media": MediaSchema(
                enabled=True,
                path=Path("relative/media"),
            ),
        },
    )

    with pytest.raises(
        ProjectValidationError,
        match="Media path must be absolute",
    ):
        service.create_project(
            invalid,
        )


def test_create_project_with_missing_media_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    invalid = project_data.model_copy(
        update={
            "media": MediaSchema(
                enabled=True,
                path=(tmp_path / "missing-media"),
            ),
        },
    )

    with pytest.raises(
        ProjectValidationError,
        match="Media directory does not exist",
    ):
        service.create_project(
            invalid,
        )


def test_create_project_with_media_file_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    media_file = tmp_path / "media.txt"

    media_file.write_text(
        "not a directory",
        encoding="utf-8",
    )

    invalid = project_data.model_copy(
        update={
            "media": MediaSchema(
                enabled=True,
                path=media_file,
            ),
        },
    )

    with pytest.raises(
        ProjectValidationError,
        match=("Media path must point to a directory"),
    ):
        service.create_project(
            invalid,
        )


def test_disabled_media_does_not_require_existing_directory_on_create(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    missing_media_path = tmp_path / "disabled-missing-media"

    data = project_data.model_copy(
        update={
            "media": MediaSchema(
                enabled=False,
                path=missing_media_path,
            ),
        },
    )

    created = service.create_project(
        data,
    )

    assert created.media.enabled is False

    assert created.media.path == missing_media_path


# =========================================================
# LIST
# =========================================================


def test_list_projects(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    service.create_project(
        project_data,
    )

    service.create_project(
        project_data.model_copy(
            update={
                "name": "second-service-test",
            },
        )
    )

    projects = service.list_projects()

    assert len(projects) == 2

    assert {project.name for project in projects} == {
        "service-test",
        "second-service-test",
    }


# =========================================================
# GET
# =========================================================


def test_get_project(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    created = service.create_project(
        project_data,
    )

    project = service.get_project(
        created.id,
    )

    assert project.id == created.id

    assert project.name == created.name


def test_get_unknown_project_fails(
    service: ProjectService,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
    ):
        service.get_project(
            "missing-project",
        )


def test_get_project_with_empty_id_fails(
    service: ProjectService,
) -> None:
    with pytest.raises(
        ProjectValidationError,
    ):
        service.get_project(
            "   ",
        )


# =========================================================
# UPDATE
# =========================================================


def test_update_project(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    updated = service.update_project(
        project.id,
        ProjectUpdateSchema(
            name="updated-project",
            enabled=False,
        ),
    )

    assert updated.name == "updated-project"

    assert updated.enabled is False


def test_update_project_database(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    project = service.create_project(
        project_data,
    )

    database_path = tmp_path / "new-db.sqlite3"

    database_path.write_bytes(b"sqlite-test")

    database = DatabaseSchema(
        type=DatabaseType.SQLITE,
        path=database_path,
    )

    updated = service.update_project(
        project.id,
        ProjectUpdateSchema(
            database=database,
        ),
    )

    assert updated.database == database


def test_update_project_with_relative_database_path_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    with pytest.raises(
        ProjectValidationError,
        match="Database path must be absolute",
    ):
        service.update_project(
            project.id,
            ProjectUpdateSchema(
                database=DatabaseSchema(
                    type=DatabaseType.SQLITE,
                    path=Path("relative/db.sqlite3"),
                ),
            ),
        )


def test_update_project_with_missing_database_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    project = service.create_project(
        project_data,
    )

    with pytest.raises(
        ProjectValidationError,
        match="Database file does not exist",
    ):
        service.update_project(
            project.id,
            ProjectUpdateSchema(
                database=DatabaseSchema(
                    type=DatabaseType.SQLITE,
                    path=(tmp_path / "missing-new.sqlite3"),
                ),
            ),
        )


def test_update_project_with_database_directory_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    project = service.create_project(
        project_data,
    )

    database_directory = tmp_path / "new-database-directory"

    database_directory.mkdir()

    with pytest.raises(
        ProjectValidationError,
        match=("Database path must point to a file"),
    ):
        service.update_project(
            project.id,
            ProjectUpdateSchema(
                database=DatabaseSchema(
                    type=DatabaseType.SQLITE,
                    path=database_directory,
                ),
            ),
        )


def test_update_project_with_relative_media_path_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    with pytest.raises(
        ProjectValidationError,
        match="Media path must be absolute",
    ):
        service.update_project(
            project.id,
            ProjectUpdateSchema(
                media=MediaSchema(
                    enabled=True,
                    path=Path("relative/media"),
                ),
            ),
        )


def test_update_project_with_missing_media_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    project = service.create_project(
        project_data,
    )

    with pytest.raises(
        ProjectValidationError,
        match="Media directory does not exist",
    ):
        service.update_project(
            project.id,
            ProjectUpdateSchema(
                media=MediaSchema(
                    enabled=True,
                    path=(tmp_path / "missing-new-media"),
                ),
            ),
        )


def test_update_project_with_media_file_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    project = service.create_project(
        project_data,
    )

    media_file = tmp_path / "new-media.txt"

    media_file.write_text(
        "not a directory",
        encoding="utf-8",
    )

    with pytest.raises(
        ProjectValidationError,
        match=("Media path must point to a directory"),
    ):
        service.update_project(
            project.id,
            ProjectUpdateSchema(
                media=MediaSchema(
                    enabled=True,
                    path=media_file,
                ),
            ),
        )


def test_disabled_media_does_not_require_existing_directory(
    service: ProjectService,
    project_data: ProjectCreateSchema,
    tmp_path: Path,
) -> None:
    project = service.create_project(
        project_data,
    )

    missing_media_path = tmp_path / "disabled-missing-media"

    updated = service.update_project(
        project.id,
        ProjectUpdateSchema(
            media=MediaSchema(
                enabled=False,
                path=missing_media_path,
            ),
        ),
    )

    assert updated.media.enabled is False

    assert updated.media.path == missing_media_path


def test_update_unknown_project_fails(
    service: ProjectService,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
    ):
        service.update_project(
            "missing-project",
            ProjectUpdateSchema(
                enabled=False,
            ),
        )


# =========================================================
# PROJECT STATUS
# =========================================================


def test_disable_project(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    updated = service.set_enabled(
        project.id,
        False,
    )

    assert updated.enabled is False


def test_enable_project(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    service.set_enabled(
        project.id,
        False,
    )

    updated = service.set_enabled(
        project.id,
        True,
    )

    assert updated.enabled is True


def test_set_status_unknown_project_fails(
    service: ProjectService,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
    ):
        service.set_enabled(
            "missing-project",
            False,
        )


# =========================================================
# DELETE
# =========================================================


def test_delete_project(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    deleted = service.delete_project(
        project.id,
    )

    assert deleted.id == project.id

    with pytest.raises(
        ProjectNotFoundError,
    ):
        service.get_project(
            project.id,
        )


def test_delete_unknown_project_fails(
    service: ProjectService,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
    ):
        service.delete_project(
            "missing-project",
        )


# =========================================================
# SCHEDULE MANAGEMENT
# =========================================================


def test_update_schedule_interval(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    updated = service.update_schedule(
        project.id,
        ScheduleUpdateSchema(
            interval=5,
        ),
    )

    assert updated.schedule.interval == 5

    assert updated.schedule.enabled == project.schedule.enabled

    assert updated.schedule.unit is project.schedule.unit


def test_update_schedule_unit(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    updated = service.update_schedule(
        project.id,
        ScheduleUpdateSchema(
            unit=ScheduleUnit.DAYS,
        ),
    )

    assert updated.schedule.unit is ScheduleUnit.DAYS

    assert updated.schedule.interval == project.schedule.interval

    assert updated.schedule.enabled == project.schedule.enabled


def test_update_schedule_interval_and_unit(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    updated = service.update_schedule(
        project.id,
        ScheduleUpdateSchema(
            interval=12,
            unit=ScheduleUnit.HOURS,
        ),
    )

    assert updated.schedule.interval == 12

    assert updated.schedule.unit is ScheduleUnit.HOURS


def test_disable_schedule(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    updated = service.set_schedule_enabled(
        project.id,
        False,
    )

    assert updated.schedule.enabled is False

    assert updated.schedule.interval == project.schedule.interval

    assert updated.schedule.unit is project.schedule.unit


def test_enable_schedule(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    service.set_schedule_enabled(
        project.id,
        False,
    )

    updated = service.set_schedule_enabled(
        project.id,
        True,
    )

    assert updated.schedule.enabled is True


def test_update_schedule_unknown_project_fails(
    service: ProjectService,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
    ):
        service.update_schedule(
            "missing-project",
            ScheduleUpdateSchema(
                interval=5,
            ),
        )


def test_update_schedule_with_empty_project_id_fails(
    service: ProjectService,
) -> None:
    with pytest.raises(
        ProjectValidationError,
    ):
        service.update_schedule(
            "   ",
            ScheduleUpdateSchema(
                interval=5,
            ),
        )


def test_empty_schedule_update_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    with pytest.raises(
        ProjectValidationError,
        match="At least one schedule field",
    ):
        service.update_schedule(
            project.id,
            ScheduleUpdateSchema(),
        )


def test_schedule_interval_must_be_positive() -> None:
    with pytest.raises(
        ValidationError,
    ):
        ScheduleUpdateSchema(
            interval=0,
        )


def test_schedule_update_preserves_other_fields(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    project = service.create_project(
        project_data,
    )

    updated = service.update_schedule(
        project.id,
        ScheduleUpdateSchema(
            interval=15,
        ),
    )

    assert updated.name == project.name

    assert updated.enabled == project.enabled

    assert updated.database == project.database

    assert updated.media == project.media

    assert updated.schedule.interval == 15
