from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from django_assistant_bot.bot.handlers.projects.create import (
    project_database_handler,
    project_media_handler,
)
from django_assistant_bot.bot.states.project import (
    ProjectCreationState,
)

# =========================================================
# BUILDERS
# =========================================================


def build_message(
    text: str,
):
    """
    Build the minimum Message-like object required by
    project path handlers.
    """

    return SimpleNamespace(
        text=text,
        answer=AsyncMock(),
    )


def build_state():
    """
    Build the minimum FSMContext-like object required by
    project path handlers.
    """

    return SimpleNamespace(
        update_data=AsyncMock(),
        set_state=AsyncMock(),
    )


def get_answer_text(
    message,
) -> str:
    """
    Return text sent through message.answer().
    """

    assert message.answer.await_count == 1

    args = message.answer.await_args.args

    assert args

    assert isinstance(
        args[0],
        str,
    )

    return args[0]


# =========================================================
# DATABASE PATH
# =========================================================


@pytest.mark.asyncio
async def test_database_handler_rejects_empty_path() -> None:
    message = build_message(
        "   ",
    )

    state = build_state()

    await project_database_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "مسیر دیتابیس نمی‌تواند خالی باشد" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_handler_rejects_relative_path() -> None:
    message = build_message(
        "relative/db.sqlite3",
    )

    state = build_state()

    await project_database_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "Absolute" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_handler_rejects_missing_file(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "missing.sqlite3"

    assert not database_path.exists()

    message = build_message(
        str(database_path),
    )

    state = build_state()

    await project_database_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "فایل دیتابیس پیدا نشد" in text

    assert str(database_path) in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_handler_rejects_directory(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "database-directory"

    database_path.mkdir()

    assert database_path.exists()

    assert database_path.is_dir()

    message = build_message(
        str(database_path),
    )

    state = build_state()

    await project_database_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "مسیر دیتابیس معتبر نیست" in text

    assert "به فایل اشاره نمی‌کند" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_database_handler_accepts_existing_file(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "db.sqlite3"

    database_path.write_bytes(b"sqlite-test")

    message = build_message(
        str(database_path),
    )

    state = build_state()

    await project_database_handler(
        message,
        state,
    )

    state.update_data.assert_awaited_once_with(
        database_path=str(database_path),
    )

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_media_path,
    )

    text = get_answer_text(
        message,
    )

    assert "Media Path" in text


@pytest.mark.asyncio
async def test_database_error_escapes_html_path(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "missing&database.sqlite3"

    assert not database_path.exists()

    message = build_message(
        str(database_path),
    )

    state = build_state()

    await project_database_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "&amp;" in text

    assert "missing&database.sqlite3" not in text

    assert "missing&amp;database.sqlite3" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


# =========================================================
# MEDIA PATH
# =========================================================


@pytest.mark.asyncio
async def test_media_handler_rejects_empty_path() -> None:
    message = build_message(
        "   ",
    )

    state = build_state()

    await project_media_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "مسیر Media نمی‌تواند خالی باشد" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_media_handler_rejects_relative_path() -> None:
    message = build_message(
        "relative/media",
    )

    state = build_state()

    await project_media_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "Absolute" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_media_handler_rejects_missing_directory(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "missing-media"

    assert not media_path.exists()

    message = build_message(
        str(media_path),
    )

    state = build_state()

    await project_media_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "پوشه Media پیدا نشد" in text

    assert str(media_path) in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_media_handler_rejects_file(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "media.txt"

    media_path.write_text(
        "not a directory",
        encoding="utf-8",
    )

    assert media_path.exists()

    assert media_path.is_file()

    message = build_message(
        str(media_path),
    )

    state = build_state()

    await project_media_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "مسیر Media معتبر نیست" in text

    assert "به پوشه اشاره نمی‌کند" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_media_handler_accepts_existing_directory(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "media"

    media_path.mkdir()

    message = build_message(
        str(media_path),
    )

    state = build_state()

    await project_media_handler(
        message,
        state,
    )

    state.update_data.assert_awaited_once_with(
        media_path=str(media_path),
    )

    state.set_state.assert_awaited_once_with(
        ProjectCreationState.waiting_for_schedule,
    )

    text = get_answer_text(
        message,
    )

    assert "زمان‌بندی Backup" in text


@pytest.mark.asyncio
async def test_media_error_escapes_html_path(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "missing&media"

    assert not media_path.exists()

    message = build_message(
        str(media_path),
    )

    state = build_state()

    await project_media_handler(
        message,
        state,
    )

    text = get_answer_text(
        message,
    )

    assert "&amp;" in text

    assert "missing&media" not in text

    assert "missing&amp;media" in text

    state.update_data.assert_not_awaited()

    state.set_state.assert_not_awaited()
