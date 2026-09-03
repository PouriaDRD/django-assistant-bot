from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import Message

from django_assistant_bot.bot.handlers.backups.history import (
    backup_history_detail_callback,
    backup_history_menu_callback,
    backup_history_project_callback,
)
from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)
from django_assistant_bot.services.backup import (
    BackupHistoryNotFoundError,
    BackupHistoryPersistenceError,
)
from django_assistant_bot.services.project import (
    ProjectNotFoundError,
)

# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
    *,
    project_id: str = "project-1",
    name: str = "Test Project",
) -> ProjectSchema:
    return ProjectSchema(
        id=project_id,
        name=name,
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=False,
            interval=1,
            unit=ScheduleUnit.DAYS,
        ),
    )


def build_history(
    tmp_path: Path,
    *,
    history_id: str = "history-1",
    project_id: str = "project-1",
    status: BackupStatus = BackupStatus.SUCCESS,
    error_message: str | None = None,
) -> BackupHistorySchema:
    now = datetime.now(
        timezone.utc,
    )

    return BackupHistorySchema(
        id=history_id,
        project_id=project_id,
        status=status,
        archive_path=(
            tmp_path / f"{history_id}.zip" if status is BackupStatus.SUCCESS else None
        ),
        database_size_bytes=100,
        media_size_bytes=200,
        archive_size_bytes=250,
        media_file_count=5,
        checksum_algorithm=("sha256" if status is BackupStatus.SUCCESS else None),
        checksum_value=("checksum-value" if status is BackupStatus.SUCCESS else None),
        error_message=error_message,
        started_at=now,
        finished_at=now,
    )


def build_message() -> Message:
    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    return message


def build_callback(
    *,
    data: str | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        data=data,
        answer=AsyncMock(),
        message=build_message(),
    )


def build_context(
    *,
    projects: list[ProjectSchema] | None = None,
    project: ProjectSchema | None = None,
    histories: list[BackupHistorySchema] | None = None,
    history: BackupHistorySchema | None = None,
    project_error: Exception | None = None,
    list_error: Exception | None = None,
    history_error: Exception | None = None,
) -> SimpleNamespace:
    project_service = Mock()

    project_service.list_projects.return_value = (
        projects if projects is not None else []
    )

    if project_error is not None:
        project_service.get_project.side_effect = project_error
    else:
        project_service.get_project.return_value = project

    history_service = Mock()

    if list_error is not None:
        history_service.list_for_project.side_effect = list_error
    else:
        history_service.list_for_project.return_value = (
            histories if histories is not None else []
        )

    if history_error is not None:
        history_service.get_history.side_effect = history_error
    else:
        history_service.get_history.return_value = history

    return SimpleNamespace(
        projects=project_service,
        backup_history=history_service,
    )


# =========================================================
# HISTORY MENU
# =========================================================


@pytest.mark.asyncio
async def test_history_menu_lists_projects(
    tmp_path: Path,
) -> None:
    projects = [
        build_project(
            tmp_path,
            project_id="project-1",
            name="Project One",
        ),
        build_project(
            tmp_path,
            project_id="project-2",
            name="Project Two",
        ),
    ]

    callback = build_callback(
        data="backup:history",
    )

    context = build_context(
        projects=projects,
    )

    await backup_history_menu_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with()

    context.projects.list_projects.assert_called_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    assert "تاریخچه بکاپ‌ها" in text

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert "bh:p:project-1:0" in callback_data

    assert "bh:p:project-2:0" in callback_data


# =========================================================
# EMPTY HISTORY
# =========================================================


@pytest.mark.asyncio
async def test_empty_project_history(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=("bh:p:" f"{project.id}:0"),
    )

    context = build_context(
        project=project,
        histories=[],
    )

    await backup_history_project_callback(
        callback,
        context,
    )

    context.projects.get_project.assert_called_once_with(
        project.id,
    )

    context.backup_history.list_for_project.assert_called_once_with(
        project.id,
        limit=6,
        offset=0,
    )

    call = callback.message.edit_text.await_args

    assert "هنوز هیچ بکاپی" in call.args[0]


# =========================================================
# FIRST PAGE
# =========================================================


@pytest.mark.asyncio
async def test_history_first_page(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    histories = [
        build_history(
            tmp_path,
            history_id=f"history-{index}",
            project_id=project.id,
        )
        for index in range(
            1,
            6,
        )
    ]

    callback = build_callback(
        data=("bh:p:" f"{project.id}:0"),
    )

    context = build_context(
        project=project,
        histories=histories,
    )

    await backup_history_project_callback(
        callback,
        context,
    )

    context.backup_history.list_for_project.assert_called_once_with(
        project.id,
        limit=6,
        offset=0,
    )

    call = callback.message.edit_text.await_args

    assert "صفحه: <b>1</b>" in call.args[0]

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert not any(value == ("bh:p:" f"{project.id}:1") for value in callback_data)


# =========================================================
# HAS NEXT PAGE
# =========================================================


@pytest.mark.asyncio
async def test_history_first_page_has_next(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    histories = [
        build_history(
            tmp_path,
            history_id=f"history-{index}",
            project_id=project.id,
        )
        for index in range(
            1,
            7,
        )
    ]

    callback = build_callback(
        data=("bh:p:" f"{project.id}:0"),
    )

    context = build_context(
        project=project,
        histories=histories,
    )

    await backup_history_project_callback(
        callback,
        context,
    )

    call = callback.message.edit_text.await_args

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert "bh:p:" f"{project.id}:1" in callback_data


# =========================================================
# SECOND PAGE
# =========================================================


@pytest.mark.asyncio
async def test_history_second_page_has_previous(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    histories = [
        build_history(
            tmp_path,
            history_id="history-6",
            project_id=project.id,
        )
    ]

    callback = build_callback(
        data=("bh:p:" f"{project.id}:1"),
    )

    context = build_context(
        project=project,
        histories=histories,
    )

    await backup_history_project_callback(
        callback,
        context,
    )

    context.backup_history.list_for_project.assert_called_once_with(
        project.id,
        limit=6,
        offset=5,
    )

    call = callback.message.edit_text.await_args

    assert "صفحه: <b>2</b>" in call.args[0]

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert "bh:p:" f"{project.id}:0" in callback_data


# =========================================================
# SUCCESS DETAIL
# =========================================================


@pytest.mark.asyncio
async def test_history_detail_success(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    history = build_history(
        tmp_path,
        history_id="history-1",
        project_id=project.id,
    )

    callback = build_callback(
        data=("bh:d:" f"{history.id}:0"),
    )

    context = build_context(
        history=history,
    )

    await backup_history_detail_callback(
        callback,
        context,
    )

    context.backup_history.get_history.assert_called_once_with(
        history.id,
    )

    call = callback.message.edit_text.await_args

    text = call.args[0]

    assert "جزئیات بکاپ" in text

    assert "✅ موفق" in text

    assert "checksum-value" in text

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert f"bh:p:{project.id}:0" in callback_data


# =========================================================
# FAILED DETAIL
# =========================================================


@pytest.mark.asyncio
async def test_history_detail_failure(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    history = build_history(
        tmp_path,
        history_id="history-failed",
        project_id=project.id,
        status=BackupStatus.FAILED,
        error_message="database unavailable",
    )

    callback = build_callback(
        data=("bh:d:" f"{history.id}:0"),
    )

    context = build_context(
        history=history,
    )

    await backup_history_detail_callback(
        callback,
        context,
    )

    context.backup_history.get_history.assert_called_once_with(
        history.id,
    )

    call = callback.message.edit_text.await_args

    text = call.args[0]

    assert "❌ ناموفق" in text

    assert "database unavailable" in text


# =========================================================
# UNKNOWN HISTORY
# =========================================================


@pytest.mark.asyncio
async def test_unknown_history_shows_alert() -> None:
    callback = build_callback(
        data="bh:d:unknown:0",
    )

    context = build_context(
        history_error=(BackupHistoryNotFoundError("not found")),
    )

    await backup_history_detail_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "تاریخچه بکاپ پیدا نشد.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# PROJECT NOT FOUND
# =========================================================


@pytest.mark.asyncio
async def test_history_project_not_found() -> None:
    callback = build_callback(
        data="bh:p:project-1:0",
    )

    context = build_context(
        project_error=(ProjectNotFoundError("not found")),
    )

    await backup_history_project_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "پروژه پیدا نشد.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# PERSISTENCE FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_history_persistence_failure(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=("bh:p:" f"{project.id}:0"),
    )

    context = build_context(
        project=project,
        list_error=(BackupHistoryPersistenceError("database error")),
    )

    await backup_history_project_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "دریافت تاریخچه بکاپ ناموفق بود.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# MALFORMED PROJECT CALLBACK
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        "bh:p:",
        "bh:p:project-1",
        "bh:p:project-1:abc",
    ],
)
async def test_invalid_history_page_callback(
    data: str,
) -> None:
    callback = build_callback(
        data=data,
    )

    context = build_context()

    await backup_history_project_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "اطلاعات صفحه نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_negative_history_page_callback() -> None:
    callback = build_callback(
        data="bh:p:project-1:-1",
    )

    context = build_context()

    await backup_history_project_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "شماره صفحه نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# MALFORMED DETAIL CALLBACK
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        "bh:d:",
        "bh:d:history-1",
        "bh:d:history-1:abc",
    ],
)
async def test_invalid_history_detail_callback(
    data: str,
) -> None:
    callback = build_callback(
        data=data,
    )

    context = build_context()

    await backup_history_detail_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "اطلاعات بکاپ نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_negative_history_detail_page() -> None:
    callback = build_callback(
        data="bh:d:history-1:-1",
    )

    context = build_context()

    await backup_history_detail_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "شماره صفحه نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()
