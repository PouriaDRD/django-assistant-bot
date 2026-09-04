from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import (
    Message,
)

from django_assistant_bot.bot.handlers.settings import (
    disable_retention_callback,
    enable_retention_callback,
    retention_keep_last_callback,
    retention_keep_last_cancel_callback,
    retention_keep_last_handler,
)
from django_assistant_bot.bot.states.settings import (
    SettingsState,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# BUILDERS
# =========================================================


def build_settings(
    *,
    retention_enabled: bool = True,
    retention_keep_last: int = 10,
) -> AppSettingsSchema:
    return AppSettingsSchema(
        retention_enabled=retention_enabled,
        retention_keep_last=retention_keep_last,
    )


def build_callback():
    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    return SimpleNamespace(
        answer=AsyncMock(),
        message=message,
    )


def build_message(
    text: str,
):
    return SimpleNamespace(
        text=text,
        answer=AsyncMock(),
    )


def build_state():
    return SimpleNamespace(
        set_state=AsyncMock(),
        clear=AsyncMock(),
    )


def build_context(
    settings: AppSettingsSchema,
):
    settings_service = Mock()

    settings_service.get_settings.return_value = settings

    settings_service.enable_retention.return_value = settings.model_copy(
        update={
            "retention_enabled": True,
        },
    )

    settings_service.disable_retention.return_value = settings.model_copy(
        update={
            "retention_enabled": False,
        },
    )

    settings_service.set_retention_keep_last.side_effect = (
        lambda value: settings.model_copy(
            update={
                "retention_keep_last": value,
            },
        )
    )

    return SimpleNamespace(
        settings=settings_service,
    )


# =========================================================
# RETENTION ENABLE
# =========================================================


@pytest.mark.asyncio
async def test_enable_retention() -> None:
    settings = build_settings(
        retention_enabled=False,
    )

    callback = build_callback()

    context = build_context(
        settings,
    )

    await enable_retention_callback(
        callback,
        context,
    )

    context.settings.enable_retention.assert_called_once_with()

    callback.answer.assert_awaited_once_with("Retention فعال شد.")

    callback.message.edit_text.assert_awaited_once()


# =========================================================
# RETENTION DISABLE
# =========================================================


@pytest.mark.asyncio
async def test_disable_retention() -> None:
    settings = build_settings(
        retention_enabled=True,
    )

    callback = build_callback()

    context = build_context(
        settings,
    )

    await disable_retention_callback(
        callback,
        context,
    )

    context.settings.disable_retention.assert_called_once_with()

    callback.answer.assert_awaited_once_with("Retention غیرفعال شد.")

    callback.message.edit_text.assert_awaited_once()


# =========================================================
# RETENTION KEEP-LAST START
# =========================================================


@pytest.mark.asyncio
async def test_retention_keep_last_flow_starts() -> None:
    settings = build_settings(
        retention_keep_last=10,
    )

    callback = build_callback()

    state = build_state()

    context = build_context(
        settings,
    )

    await retention_keep_last_callback(
        callback,
        state,
        context,
    )

    context.settings.get_settings.assert_called_once_with()

    state.set_state.assert_awaited_once_with(
        SettingsState.waiting_for_retention_keep_last,
    )

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()


# =========================================================
# VALID VALUE
# =========================================================


@pytest.mark.asyncio
async def test_retention_keep_last_accepts_valid_value() -> None:
    settings = build_settings(
        retention_keep_last=10,
    )

    message = build_message(
        "25",
    )

    state = build_state()

    context = build_context(
        settings,
    )

    await retention_keep_last_handler(
        message,
        state,
        context,
    )

    context.settings.set_retention_keep_last.assert_called_once_with(
        25,
    )

    state.clear.assert_awaited_once_with()

    message.answer.assert_awaited_once()

    sent_text = message.answer.await_args.args[0]

    assert "روی 25 تنظیم شد" in sent_text


# =========================================================
# INVALID TEXT
# =========================================================


@pytest.mark.asyncio
async def test_retention_keep_last_rejects_non_numeric_value() -> None:
    settings = build_settings()

    message = build_message(
        "hello",
    )

    state = build_state()

    context = build_context(
        settings,
    )

    await retention_keep_last_handler(
        message,
        state,
        context,
    )

    context.settings.set_retention_keep_last.assert_not_called()

    state.clear.assert_not_awaited()

    message.answer.assert_awaited_once()

    sent_text = message.answer.await_args.args[0]

    assert "مقدار واردشده معتبر نیست" in sent_text


# =========================================================
# INVALID ZERO
# =========================================================


@pytest.mark.asyncio
async def test_retention_keep_last_rejects_zero() -> None:
    settings = build_settings()

    message = build_message(
        "0",
    )

    state = build_state()

    context = build_context(
        settings,
    )

    await retention_keep_last_handler(
        message,
        state,
        context,
    )

    context.settings.set_retention_keep_last.assert_not_called()

    state.clear.assert_not_awaited()

    message.answer.assert_awaited_once_with("❌ تعداد بکاپ‌ها باید حداقل 1 باشد.")


# =========================================================
# INVALID NEGATIVE
# =========================================================


@pytest.mark.asyncio
async def test_retention_keep_last_rejects_negative() -> None:
    settings = build_settings()

    message = build_message(
        "-5",
    )

    state = build_state()

    context = build_context(
        settings,
    )

    await retention_keep_last_handler(
        message,
        state,
        context,
    )

    context.settings.set_retention_keep_last.assert_not_called()

    state.clear.assert_not_awaited()

    message.answer.assert_awaited_once_with("❌ تعداد بکاپ‌ها باید حداقل 1 باشد.")


# =========================================================
# CANCEL
# =========================================================


@pytest.mark.asyncio
async def test_retention_keep_last_cancel() -> None:
    settings = build_settings()

    callback = build_callback()

    state = build_state()

    context = build_context(
        settings,
    )

    await retention_keep_last_cancel_callback(
        callback,
        state,
        context,
    )

    state.clear.assert_awaited_once_with()

    context.settings.get_settings.assert_called_once_with()

    callback.answer.assert_awaited_once_with("تغییر مقدار لغو شد.")

    callback.message.edit_text.assert_awaited_once()
