from __future__ import annotations

from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.keyboards.settings import (
    BOT_ENABLE_CALLBACK,
)
from django_assistant_bot.bot.middlewares.bot_enabled import (
    BotEnabledMiddleware,
)
from django_assistant_bot.services.settings import (
    SettingsPersistenceError,
)

# =========================================================
# BUILDERS
# =========================================================


def build_settings(
    *,
    enabled: bool = True,
    error: Exception | None = None,
) -> Mock:
    settings = Mock()

    if error is not None:
        settings.is_bot_enabled.side_effect = error

    else:
        settings.is_bot_enabled.return_value = enabled

    return settings


def build_message() -> Mock:
    message = Mock(
        spec=Message,
    )

    message.answer = AsyncMock()

    return message


def build_callback(
    *,
    data: str,
) -> Mock:
    callback = Mock(
        spec=CallbackQuery,
    )

    callback.data = data

    callback.answer = AsyncMock()

    return callback


# =========================================================
# ENABLED
# =========================================================


@pytest.mark.asyncio
async def test_enabled_bot_allows_message() -> None:
    settings = build_settings(
        enabled=True,
    )

    middleware = BotEnabledMiddleware(
        settings=settings,
    )

    handler = AsyncMock(
        return_value="handled",
    )

    message = build_message()

    result = await middleware(
        handler,
        message,
        {},
    )

    assert result == "handled"

    settings.is_bot_enabled.assert_called_once_with()

    handler.assert_awaited_once_with(
        message,
        {},
    )

    message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_enabled_bot_allows_callback() -> None:
    settings = build_settings(
        enabled=True,
    )

    middleware = BotEnabledMiddleware(
        settings=settings,
    )

    handler = AsyncMock(
        return_value="handled",
    )

    callback = build_callback(
        data="projects",
    )

    result = await middleware(
        handler,
        callback,
        {},
    )

    assert result == "handled"

    handler.assert_awaited_once_with(
        callback,
        {},
    )

    callback.answer.assert_not_awaited()


# =========================================================
# DISABLED
# =========================================================


@pytest.mark.asyncio
async def test_disabled_bot_blocks_message() -> None:
    settings = build_settings(
        enabled=False,
    )

    middleware = BotEnabledMiddleware(
        settings=settings,
    )

    handler = AsyncMock()

    message = build_message()

    result = await middleware(
        handler,
        message,
        {},
    )

    assert result is None

    handler.assert_not_awaited()

    message.answer.assert_awaited_once()

    call = message.answer.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "ربات غیرفعال است" in text

    assert keyboard.inline_keyboard[0][0].callback_data == BOT_ENABLE_CALLBACK


@pytest.mark.asyncio
async def test_disabled_bot_blocks_normal_callback() -> None:
    settings = build_settings(
        enabled=False,
    )

    middleware = BotEnabledMiddleware(
        settings=settings,
    )

    handler = AsyncMock()

    callback = build_callback(
        data="projects",
    )

    result = await middleware(
        handler,
        callback,
        {},
    )

    assert result is None

    handler.assert_not_awaited()

    callback.answer.assert_awaited_once_with(
        ("🔴 ربات غیرفعال است.\n" "ابتدا ربات را فعال کنید."),
        show_alert=True,
    )


# =========================================================
# RE-ENABLE EXCEPTION
# =========================================================


@pytest.mark.asyncio
async def test_disabled_bot_allows_enable_callback() -> None:
    settings = build_settings(
        enabled=False,
    )

    middleware = BotEnabledMiddleware(
        settings=settings,
    )

    handler = AsyncMock(
        return_value="enabled",
    )

    callback = build_callback(
        data=BOT_ENABLE_CALLBACK,
    )

    result = await middleware(
        handler,
        callback,
        {},
    )

    assert result == "enabled"

    handler.assert_awaited_once_with(
        callback,
        {},
    )

    callback.answer.assert_not_awaited()


# =========================================================
# SETTINGS FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_settings_failure_blocks_message() -> None:
    settings = build_settings(
        error=SettingsPersistenceError("database unavailable"),
    )

    middleware = BotEnabledMiddleware(
        settings=settings,
    )

    handler = AsyncMock()

    message = build_message()

    result = await middleware(
        handler,
        message,
        {},
    )

    assert result is None

    handler.assert_not_awaited()

    message.answer.assert_awaited_once_with("⚠️ خطا در بررسی وضعیت ربات.")


@pytest.mark.asyncio
async def test_settings_failure_blocks_callback() -> None:
    settings = build_settings(
        error=SettingsPersistenceError("database unavailable"),
    )

    middleware = BotEnabledMiddleware(
        settings=settings,
    )

    handler = AsyncMock()

    callback = build_callback(
        data="projects",
    )

    result = await middleware(
        handler,
        callback,
        {},
    )

    assert result is None

    handler.assert_not_awaited()

    callback.answer.assert_awaited_once_with(
        "⚠️ خطا در بررسی وضعیت ربات.",
        show_alert=True,
    )
