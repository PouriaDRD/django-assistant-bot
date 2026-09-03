from __future__ import annotations

from pathlib import Path

import pytest

from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.database.session import SessionManager
from django_assistant_bot.repositories.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
)
from django_assistant_bot.repositories.project import ProjectRepository
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectCreateSchema,
    ProjectUpdateSchema,
    ScheduleSchema,
)


@pytest.fixture()
def repository(
    session_manager: SessionManager,
) -> ProjectRepository:
    return ProjectRepository(
        session_manager,
    )


@pytest.fixture()
def project_data() -> ProjectCreateSchema:
    return ProjectCreateSchema(
        name="test-project",
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=Path("/srv/test/db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=True,
            path=Path("/srv/test/media"),
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=30,
            unit=ScheduleUnit.MINUTES,
        ),
    )


def test_create_project(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    project = repository.create(
        project_data,
    )

    assert project.id
    assert project.name == "test-project"
    assert project.enabled is True

    assert project.database.type is DatabaseType.SQLITE

    assert project.database.path == Path("/srv/test/db.sqlite3")

    assert project.media.path == Path("/srv/test/media")

    assert project.schedule.interval == 30
    assert project.schedule.unit is ScheduleUnit.MINUTES


def test_get_project_by_id(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    created = repository.create(
        project_data,
    )

    project = repository.get_by_id(
        created.id,
    )

    assert project is not None
    assert project.id == created.id
    assert project.name == created.name


def test_get_project_by_name(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    repository.create(
        project_data,
    )

    project = repository.get_by_name("test-project")

    assert project is not None
    assert project.name == "test-project"


def test_get_unknown_project_returns_none(
    repository: ProjectRepository,
) -> None:
    project = repository.get_by_id(
        "missing-project",
    )

    assert project is None


def test_list_projects(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    repository.create(
        project_data,
    )

    repository.create(
        project_data.model_copy(
            update={
                "name": "second-project",
            },
        )
    )

    projects = repository.list_all()

    assert len(projects) == 2

    assert {project.name for project in projects} == {
        "test-project",
        "second-project",
    }


def test_duplicate_project_name_is_rejected(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    repository.create(
        project_data,
    )

    with pytest.raises(
        DuplicateEntityError,
    ):
        repository.create(project_data)


def test_project_name_is_case_insensitive(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    repository.create(
        project_data,
    )

    with pytest.raises(
        DuplicateEntityError,
    ):
        repository.create(
            project_data.model_copy(
                update={
                    "name": "TEST-PROJECT",
                },
            )
        )


def test_update_project(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    project = repository.create(
        project_data,
    )

    updated = repository.update(
        project.id,
        ProjectUpdateSchema(
            name="updated-project",
            enabled=False,
        ),
    )

    assert updated.name == "updated-project"
    assert updated.enabled is False


def test_update_unknown_project_fails(
    repository: ProjectRepository,
) -> None:
    with pytest.raises(
        EntityNotFoundError,
    ):
        repository.update(
            "missing",
            ProjectUpdateSchema(
                enabled=False,
            ),
        )


def test_set_project_enabled(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    project = repository.create(
        project_data,
    )

    disabled = repository.set_enabled(
        project.id,
        False,
    )

    assert disabled.enabled is False

    enabled = repository.set_enabled(
        project.id,
        True,
    )

    assert enabled.enabled is True


def test_delete_project(
    repository: ProjectRepository,
    project_data: ProjectCreateSchema,
) -> None:
    project = repository.create(
        project_data,
    )

    deleted = repository.delete(
        project.id,
    )

    assert deleted.id == project.id

    assert (
        repository.get_by_id(
            project.id,
        )
        is None
    )


def test_delete_unknown_project_fails(
    repository: ProjectRepository,
) -> None:
    with pytest.raises(
        EntityNotFoundError,
    ):
        repository.delete(
            "missing-project",
        )
