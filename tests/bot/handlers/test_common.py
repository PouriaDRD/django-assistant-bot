from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.handlers.common import (
    build_main_menu_message,
    build_start_message,
    main_menu_callback,
    menu_handler,
    start_handler,
)

# =========================================================
# BUILDERS
# =========================================================


def build_context(
    *,
    bot_enabled: bool = True,
    backup_enabled: bool = True,
    project_count: int = 0,
) -> tuple[
    ApplicationContext,
    Mock,
    Mock,
]:
    """
    Build the minimum ApplicationContext test double
    required by common handler tests.

    Returns:
    - ApplicationContext test double
    - projects service mock
    - settings service mock
    """

    projects = Mock()

    projects.list_projects.return_value = [object() for _ in range(project_count)]

    settings = Mock()

    settings.get_settings.return_value = SimpleNamespace(
        bot_enabled=bot_enabled,
        backup_enabled=backup_enabled,
    )

    context = SimpleNamespace(
        projects=projects,
        settings=settings,
    )

    return (
        cast(
            ApplicationContext,
            context,
        ),
        projects,
        settings,
    )


def build_message() -> Message:
    """
    Build an aiogram Message test double.
    """

    message = cast(
        Message,
        Mock(
            spec=Message,
        ),
    )

    message.answer = AsyncMock()
    message.edit_text = AsyncMock()

    return message


def build_callback(
    message: Message,
) -> CallbackQuery:
    """
    Build an aiogram CallbackQuery test double.
    """

    callback = cast(
        CallbackQuery,
        Mock(
            spec=CallbackQuery,
        ),
    )

    callback.answer = AsyncMock()
    callback.message = message

    return callback


# =========================================================
# MOCK ACCESSORS
# =========================================================


def get_answer_mock(
    message: Message,
) -> AsyncMock:
    """
    Return Message.answer as AsyncMock.
    """

    return cast(
        AsyncMock,
        message.answer,
    )


def get_edit_text_mock(
    message: Message,
) -> AsyncMock:
    """
    Return Message.edit_text as AsyncMock.
    """

    return cast(
        AsyncMock,
        message.edit_text,
    )


def get_callback_answer_mock(
    callback: CallbackQuery,
) -> AsyncMock:
    """
    Return CallbackQuery.answer as AsyncMock.
    """

    return cast(
        AsyncMock,
        callback.answer,
    )


# =========================================================
# START MESSAGE
# =========================================================


def test_start_message_is_standalone() -> None:
    text = build_start_message()

    assert "Django Assistant Bot" in text

    assert "/menu" in text

    assert "وضعیت ربات" not in text

    assert "وضعیت بکاپ" not in text

    assert "تعداد پروژه‌ها" not in text


# =========================================================
# MAIN MENU MESSAGE
# =========================================================


def test_main_menu_message_uses_live_status() -> None:
    (
        context,
        projects,
        settings,
    ) = build_context(
        bot_enabled=True,
        backup_enabled=False,
        project_count=3,
    )

    text = build_main_menu_message(
        context,
    )

    assert "Django Assistant Bot" in text

    assert "وضعیت ربات: 🟢 فعال" in text

    assert "وضعیت بکاپ: 🔴 غیرفعال" in text

    assert "تعداد پروژه‌ها: <b>3</b>" in text

    projects.list_projects.assert_called_once_with()

    settings.get_settings.assert_called_once_with()


# =========================================================
# START HANDLER
# =========================================================


@pytest.mark.asyncio
async def test_start_handler_does_not_show_main_menu() -> None:
    message = build_message()

    await start_handler(
        message,
    )

    answer = get_answer_mock(
        message,
    )

    answer.assert_awaited_once()

    call = answer.await_args

    assert call is not None

    text = call.args[0]

    assert "/menu" in text

    assert "reply_markup" not in call.kwargs


# =========================================================
# MENU HANDLER
# =========================================================


@pytest.mark.asyncio
async def test_menu_handler_shows_dashboard_and_keyboard() -> None:
    message = build_message()

    (
        context,
        _,
        _,
    ) = build_context(
        bot_enabled=True,
        backup_enabled=True,
        project_count=2,
    )

    await menu_handler(
        message,
        context,
    )

    answer = get_answer_mock(
        message,
    )

    answer.assert_awaited_once()

    call = answer.await_args

    assert call is not None

    text = call.args[0]

    assert "وضعیت ربات: 🟢 فعال" in text

    assert "وضعیت بکاپ: 🟢 فعال" in text

    assert "تعداد پروژه‌ها: <b>2</b>" in text

    assert call.kwargs["reply_markup"] is not None


# =========================================================
# MAIN MENU CALLBACK
# =========================================================


@pytest.mark.asyncio
async def test_main_menu_callback_restores_dashboard() -> None:
    message = build_message()

    callback = build_callback(
        message,
    )

    (
        context,
        _,
        _,
    ) = build_context(
        bot_enabled=True,
        backup_enabled=True,
        project_count=4,
    )

    await main_menu_callback(
        callback,
        context,
    )

    callback_answer = get_callback_answer_mock(
        callback,
    )

    callback_answer.assert_awaited_once_with()

    edit_text = get_edit_text_mock(
        message,
    )

    edit_text.assert_awaited_once()

    call = edit_text.await_args

    assert call is not None

    text = call.args[0]

    assert "تعداد پروژه‌ها: <b>4</b>" in text

    assert call.kwargs["reply_markup"] is not None
