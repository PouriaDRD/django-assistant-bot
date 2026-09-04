from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import Message

from django_assistant_bot.bot.handlers.settings import (
    compression_level_callback,
    set_compression_level_callback,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# BUILDERS
# =========================================================


def build_settings(
    *,
    compression_level: int = 6,
) -> AppSettingsSchema:
    return AppSettingsSchema(
        compression_level=compression_level,
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
    settings: AppSettingsSchema,
):
    settings_service = Mock()

    settings_service.get_settings.return_value = settings

    settings_service.set_compression_level.side_effect = (
        lambda level: settings.model_copy(
            update={
                "compression_level": level,
            },
        )
    )

    return SimpleNamespace(
        settings=settings_service,
    )


# =========================================================
# MENU
# =========================================================


@pytest.mark.asyncio
async def test_compression_menu_opens() -> None:
    settings = build_settings(
        compression_level=6,
    )

    callback = build_callback(
        "settings:compression:level",
    )

    context = build_context(
        settings,
    )

    await compression_level_callback(
        callback,
        context,
    )

    context.settings.get_settings.assert_called_once_with()

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()

    text = callback.message.edit_text.await_args.args[0]

    assert "سطح فشرده‌سازی" in text

    assert "مقدار فعلی: <b>6</b>" in text


# =========================================================
# VALID VALUES
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "level",
    [
        0,
        1,
        3,
        6,
        9,
    ],
)
async def test_set_valid_compression_level(
    level: int,
) -> None:
    settings = build_settings(
        compression_level=6,
    )

    callback = build_callback(
        f"settings:compression:set:{level}",
    )

    context = build_context(
        settings,
    )

    await set_compression_level_callback(
        callback,
        context,
    )

    context.settings.set_compression_level.assert_called_once_with(
        level,
    )

    callback.answer.assert_awaited_once_with("سطح فشرده‌سازی " f"روی {level} تنظیم شد.")

    callback.message.edit_text.assert_awaited_once()


# =========================================================
# INVALID TEXT
# =========================================================


@pytest.mark.asyncio
async def test_rejects_non_numeric_compression_level() -> None:
    settings = build_settings()

    callback = build_callback(
        "settings:compression:set:abc",
    )

    context = build_context(
        settings,
    )

    await set_compression_level_callback(
        callback,
        context,
    )

    context.settings.set_compression_level.assert_not_called()

    callback.answer.assert_awaited_once_with(
        "سطح فشرده‌سازی نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# OUT OF RANGE
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "level",
    [
        -1,
        10,
        99,
    ],
)
async def test_rejects_out_of_range_compression_level(
    level: int,
) -> None:
    settings = build_settings()

    callback = build_callback(
        f"settings:compression:set:{level}",
    )

    context = build_context(
        settings,
    )

    await set_compression_level_callback(
        callback,
        context,
    )

    context.settings.set_compression_level.assert_not_called()

    callback.answer.assert_awaited_once_with(
        "سطح فشرده‌سازی باید بین 0 تا 9 باشد.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()
