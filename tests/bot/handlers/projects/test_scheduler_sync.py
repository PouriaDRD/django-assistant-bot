from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import Message

from django_assistant_bot.bot.handlers.projects.delete import (
    project_delete_callback,
)
from django_assistant_bot.bot.handlers.projects.status import (
    project_disable_callback,
    project_enable_callback,
)
from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)


def build_project(
    tmp_path: Path,
    *,
    enabled: bool = True,
) -> ProjectSchema:
    return ProjectSchema(
        id="project-1",
        name="Test Project",
        enabled=enabled,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=1,
            unit=ScheduleUnit.HOURS,
        ),
    )


def build_callback(
    data: str,
):
    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    return SimpleNamespace(
        data=data,
        answer=AsyncMock(),
        message=message,
    )


def build_context(
    *,
    project: ProjectSchema,
):
    projects = Mock()
    scheduler = Mock()

    projects.set_enabled.return_value = project

    projects.delete_project.return_value = project

    return SimpleNamespace(
        projects=projects,
        scheduler=scheduler,
    )


@pytest.mark.asyncio
async def test_enable_project_syncs_scheduler(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        enabled=True,
    )

    context = build_context(
        project=project,
    )

    callback = build_callback("project:enable:project-1")

    await project_enable_callback(
        callback,
        context,
    )

    context.projects.set_enabled.assert_called_once_with(
        "project-1",
        True,
    )

    context.scheduler.sync_project.assert_called_once_with(
        project,
    )


@pytest.mark.asyncio
async def test_disable_project_syncs_scheduler(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        enabled=False,
    )

    context = build_context(
        project=project,
    )

    callback = build_callback("project:disable:project-1")

    await project_disable_callback(
        callback,
        context,
    )

    context.projects.set_enabled.assert_called_once_with(
        "project-1",
        False,
    )

    context.scheduler.sync_project.assert_called_once_with(
        project,
    )


@pytest.mark.asyncio
async def test_delete_project_removes_scheduler_job(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    context = build_context(
        project=project,
    )

    callback = build_callback("project:delete:project-1")

    await project_delete_callback(
        callback,
        context,
    )

    context.projects.delete_project.assert_called_once_with("project-1")

    context.scheduler.remove_project.assert_called_once_with(
        project.id,
    )


@pytest.mark.asyncio
async def test_status_change_survives_scheduler_failure(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        enabled=True,
    )

    context = build_context(
        project=project,
    )

    context.scheduler.sync_project.side_effect = RuntimeError("scheduler unavailable")

    callback = build_callback("project:enable:project-1")

    await project_enable_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with("پروژه فعال شد.")


@pytest.mark.asyncio
async def test_delete_survives_scheduler_cleanup_failure(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    context = build_context(
        project=project,
    )

    context.scheduler.remove_project.side_effect = RuntimeError("scheduler unavailable")

    callback = build_callback("project:delete:project-1")

    await project_delete_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with("پروژه حذف شد.")
