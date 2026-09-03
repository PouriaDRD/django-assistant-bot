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

from django_assistant_bot.bot.handlers.projects.backup import (
    project_backup_callback,
)
from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)
from django_assistant_bot.services.backup import (
    BackupAlreadyRunningError,
    BackupDisabledError,
    BackupExecutionError,
    BackupHistoryError,
    ProjectBackupDisabledError,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
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
) -> ProjectSchema:
    return ProjectSchema(
        id=project_id,
        name="Test Project",
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
            enabled=True,
            interval=1,
            unit=ScheduleUnit.HOURS,
        ),
    )


def build_result(
    tmp_path: Path,
    *,
    project_id: str = "project-1",
) -> BackupResult:
    archive_path = tmp_path / "backup.zip"

    archive_path.write_bytes(b"backup-content")

    started_at = datetime.now(
        timezone.utc,
    )

    finished_at = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id=project_id,
        project_name="Test Project",
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        started_at=started_at,
        finished_at=finished_at,
        database_size_bytes=100,
        media_size_bytes=200,
        archive_size_bytes=300,
        media_file_count=3,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="checksum-value",
        ),
    )


def build_message() -> Message:
    """
    Build a Message-compatible test double.

    Mock(spec=Message) reports itself as a Message instance,
    which allows the handler's isinstance guard to behave the
    same way it does with a real aiogram Message.
    """

    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    message.answer_document = AsyncMock()

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
    project: ProjectSchema,
    backup_result: BackupResult | None = None,
    backup_error: Exception | None = None,
    project_error: Exception | None = None,
) -> SimpleNamespace:
    projects = Mock()

    if project_error is not None:
        projects.get_project.side_effect = project_error

    else:
        projects.get_project.return_value = project

    backups = Mock()

    if backup_error is not None:
        backups.run.side_effect = backup_error

    else:
        backups.run.return_value = backup_result

    return SimpleNamespace(
        projects=projects,
        backups=backups,
    )


async def run_in_current_thread(
    function,
    *args,
):
    """
    Test replacement for asyncio.to_thread.

    Executes synchronously while preserving the async
    interface expected by the handler.
    """

    return function(
        *args,
    )


# =========================================================
# SUCCESS
# =========================================================


@pytest.mark.asyncio
async def test_backup_success_sends_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    result = build_result(
        tmp_path,
    )

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    context = build_context(
        project=project,
        backup_result=result,
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.projects.get_project.assert_called_once_with(
        project.id,
    )

    context.backups.run.assert_called_once_with(
        project.id,
    )

    callback.answer.assert_awaited_once_with(
        "تهیه بکاپ شروع شد.",
    )

    callback.message.answer_document.assert_awaited_once()

    assert callback.message.edit_text.await_count == 2

    first_call = callback.message.edit_text.await_args_list[0]

    assert "تهیه بکاپ شروع شد" in first_call.args[0]

    final_call = callback.message.edit_text.await_args_list[-1]

    final_text = final_call.args[0]

    assert "بکاپ با موفقیت انجام شد" in final_text

    assert "Test Project" in final_text

    assert "checksum-value" in final_text


# =========================================================
# INVALID CALLBACK
# =========================================================


@pytest.mark.asyncio
async def test_missing_callback_data_is_ignored(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=None,
    )

    context = build_context(
        project=project,
    )

    await project_backup_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with()

    context.projects.get_project.assert_not_called()

    context.backups.run.assert_not_called()

    callback.message.edit_text.assert_not_awaited()

    callback.message.answer_document.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_project_id_is_rejected(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data="project:backup:   ",
    )

    context = build_context(
        project=project,
    )

    await project_backup_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "شناسه پروژه نامعتبر است.",
        show_alert=True,
    )

    context.projects.get_project.assert_not_called()

    context.backups.run.assert_not_called()

    callback.message.edit_text.assert_not_awaited()

    callback.message.answer_document.assert_not_awaited()


# =========================================================
# PROJECT NOT FOUND
# =========================================================


@pytest.mark.asyncio
async def test_unknown_project_shows_alert(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data="project:backup:unknown",
    )

    context = build_context(
        project=project,
        project_error=ProjectNotFoundError("Project not found."),
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.projects.get_project.assert_called_once_with(
        "unknown",
    )

    callback.answer.assert_awaited_once_with(
        "پروژه پیدا نشد.",
        show_alert=True,
    )

    context.backups.run.assert_not_called()

    callback.message.edit_text.assert_not_awaited()

    callback.message.answer_document.assert_not_awaited()


# =========================================================
# BACKUP DISABLED
# =========================================================


@pytest.mark.asyncio
async def test_backup_disabled_is_handled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    context = build_context(
        project=project,
        backup_error=BackupDisabledError("disabled"),
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.backups.run.assert_called_once_with(
        project.id,
    )

    assert callback.message.edit_text.await_count == 2

    final_call = callback.message.edit_text.await_args_list[-1]

    assert "سیستم بکاپ غیرفعال است" in final_call.args[0]

    callback.message.answer_document.assert_not_awaited()


# =========================================================
# ALREADY RUNNING
# =========================================================


@pytest.mark.asyncio
async def test_running_backup_is_handled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    context = build_context(
        project=project,
        backup_error=BackupAlreadyRunningError("already running"),
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.backups.run.assert_called_once_with(
        project.id,
    )

    final_call = callback.message.edit_text.await_args_list[-1]

    assert "بکاپ در حال اجراست" in final_call.args[0]

    callback.message.answer_document.assert_not_awaited()


# =========================================================
# EXECUTION FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_backup_execution_failure_is_handled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    context = build_context(
        project=project,
        backup_error=BackupExecutionError("backup failed"),
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.backups.run.assert_called_once_with(
        project.id,
    )

    final_call = callback.message.edit_text.await_args_list[-1]

    assert "تهیه بکاپ ناموفق بود" in final_call.args[0]

    callback.message.answer_document.assert_not_awaited()


# =========================================================
# HISTORY FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_history_failure_is_handled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    context = build_context(
        project=project,
        backup_error=BackupHistoryError("history failed"),
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.backups.run.assert_called_once_with(
        project.id,
    )

    final_call = callback.message.edit_text.await_args_list[-1]

    assert "ثبت تاریخچه" in final_call.args[0]

    callback.message.answer_document.assert_not_awaited()


# =========================================================
# ARCHIVE MISSING
# =========================================================


@pytest.mark.asyncio
async def test_missing_archive_is_handled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    result = build_result(
        tmp_path,
    )

    result.archive_path.unlink()

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    context = build_context(
        project=project,
        backup_result=result,
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.backups.run.assert_called_once_with(
        project.id,
    )

    final_call = callback.message.edit_text.await_args_list[-1]

    assert "فایل بکاپ پیدا نشد" in final_call.args[0]

    callback.message.answer_document.assert_not_awaited()


# =========================================================
# TELEGRAM DELIVERY FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_document_delivery_failure_is_handled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    result = build_result(
        tmp_path,
    )

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    callback.message.answer_document.side_effect = RuntimeError("telegram unavailable")

    context = build_context(
        project=project,
        backup_result=result,
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    context.backups.run.assert_called_once_with(
        project.id,
    )

    callback.message.answer_document.assert_awaited_once()

    final_call = callback.message.edit_text.await_args_list[-1]

    assert "ارسال فایل به تلگرام ناموفق بود" in final_call.args[0]


@pytest.mark.asyncio
async def test_disabled_project_is_handled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = build_project(
        tmp_path,
    )

    project = project.model_copy(
        update={
            "enabled": False,
        }
    )

    callback = build_callback(
        data=(f"project:backup:" f"{project.id}"),
    )

    context = build_context(
        project=project,
        backup_error=(ProjectBackupDisabledError("Project is disabled.")),
    )

    monkeypatch.setattr(
        "django_assistant_bot.bot.handlers." "projects.backup.asyncio.to_thread",
        run_in_current_thread,
    )

    await project_backup_callback(
        callback,
        context,
    )

    final_call = callback.message.edit_text.await_args_list[-1]

    assert "پروژه غیرفعال است" in final_call.args[0]

    callback.message.answer_document.assert_not_awaited()
