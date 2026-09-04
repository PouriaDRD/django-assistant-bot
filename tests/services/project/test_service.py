from __future__ import annotations

import pytest
from pathlib import Path
from pydantic import ValidationError


from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.database.session import SessionManager
from django_assistant_bot.repositories.project import ProjectRepository

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
def project_data() -> ProjectCreateSchema:
    return ProjectCreateSchema(
        name="service-test",
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=Path(r"C:\projects\service-test\db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=True,
            path=Path(r"C:\projects\service-test\media"),
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=30,
            unit=ScheduleUnit.MINUTES,
        ),
    )


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


def test_create_project_with_relative_database_path_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    invalid = project_data.model_copy(
        update={
            "database": DatabaseSchema(
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


def test_create_project_with_relative_media_path_fails(
    service: ProjectService,
    project_data: ProjectCreateSchema,
) -> None:
    invalid = project_data.model_copy(
        update={
            "media": MediaSchema(
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
) -> None:
    project = service.create_project(
        project_data,
    )

    database = DatabaseSchema(
        type=DatabaseType.SQLITE,
        path=Path(r"C:\projects\new\db.sqlite3"),
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
    ):
        service.update_project(
            project.id,
            ProjectUpdateSchema(
                database=DatabaseSchema(
                    path=Path("relative/db.sqlite3"),
                ),
            ),
        )


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

    # Unchanged values must be preserved.
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
