from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import Message

from django_assistant_bot.bot.handlers.projects.create import (
    project_create_confirm,
)
from django_assistant_bot.core.environment import (
    AppEnvironment,
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

# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
) -> ProjectSchema:
    """
    Build project returned by ProjectService.
    """

    return ProjectSchema(
        id="project-1",
        name="Test Project",
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=True,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=1,
            unit=ScheduleUnit.MINUTES,
        ),
    )


def build_callback():
    """
    Build minimal callback used by project creation.
    """

    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    return SimpleNamespace(
        data="project:create:confirm",
        answer=AsyncMock(),
        message=message,
    )


def build_state(
    tmp_path: Path,
):
    """
    Build project creation FSM data.
    """

    return SimpleNamespace(
        get_data=AsyncMock(
            return_value={
                "project_name": ("Test Project"),
                "database_path": str(tmp_path / "db.sqlite3"),
                "media_path": str(tmp_path / "media"),
                "schedule": {
                    "enabled": True,
                    "interval": 1,
                    "unit": "minutes",
                },
            }
        ),
        clear=AsyncMock(),
    )


def build_context(
    project: ProjectSchema,
):
    """
    Build minimal ApplicationContext-compatible object.

    Development environment is intentional because these
    tests use a one-minute schedule.
    """

    projects = Mock()

    scheduler = Mock()

    projects.create_project.return_value = project

    return SimpleNamespace(
        environment=SimpleNamespace(
            environment=(AppEnvironment.DEVELOPMENT),
        ),
        projects=projects,
        scheduler=scheduler,
    )


# =========================================================
# SCHEDULER SYNC
# =========================================================


@pytest.mark.asyncio
async def test_project_creation_syncs_scheduler(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback()

    state = build_state(
        tmp_path,
    )

    context = build_context(
        project,
    )

    await project_create_confirm(
        callback,
        state,
        context,
    )

    context.projects.create_project.assert_called_once()

    context.scheduler.sync_project.assert_called_once_with(
        project,
    )

    state.clear.assert_awaited_once_with()

    callback.answer.assert_awaited_once_with("پروژه با موفقیت ایجاد شد.")

    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_project_creation_survives_scheduler_failure(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback()

    state = build_state(
        tmp_path,
    )

    context = build_context(
        project,
    )

    context.scheduler.sync_project.side_effect = RuntimeError("scheduler unavailable")

    await project_create_confirm(
        callback,
        state,
        context,
    )

    context.projects.create_project.assert_called_once()

    context.scheduler.sync_project.assert_called_once_with(
        project,
    )

    # Project persistence must remain successful even when
    # scheduler synchronization temporarily fails.
    state.clear.assert_awaited_once_with()

    callback.answer.assert_awaited_once_with("پروژه با موفقیت ایجاد شد.")

    callback.message.edit_text.assert_awaited_once()
