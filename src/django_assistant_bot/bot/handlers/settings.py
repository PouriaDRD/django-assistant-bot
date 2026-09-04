from __future__ import annotations

import logging

from aiogram import (
    F,
    Router,
)
from aiogram.fsm.context import (
    FSMContext,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)
from pydantic import ValidationError

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.settings import (
    format_bot_disabled,
    format_compression_level_menu,
    format_retention_keep_last_prompt,
    format_settings_menu,
)
from django_assistant_bot.bot.handlers.common import (
    build_welcome_message,
)
from django_assistant_bot.bot.keyboards.main import (
    main_menu_keyboard,
)
from django_assistant_bot.bot.keyboards.settings import (
    BACKUP_DISABLE_CALLBACK,
    BACKUP_ENABLE_CALLBACK,
    BOT_DISABLE_CALLBACK,
    BOT_ENABLE_CALLBACK,
    COMPRESSION_LEVEL_CALLBACK,
    COMPRESSION_LEVEL_SET_PREFIX,
    RETENTION_DISABLE_CALLBACK,
    RETENTION_ENABLE_CALLBACK,
    RETENTION_KEEP_LAST_CALLBACK,
    RETENTION_KEEP_LAST_CANCEL_CALLBACK,
    SETTINGS_CALLBACK,
    compression_level_keyboard,
    disabled_bot_keyboard,
    retention_keep_last_keyboard,
    settings_keyboard,
)
from django_assistant_bot.bot.states.settings import (
    SettingsState,
)
from django_assistant_bot.services.settings import (
    SettingsPersistenceError,
)

# =========================================================
# LOGGER
# =========================================================


logger = logging.getLogger(
    __name__,
)


# =========================================================
# ROUTER
# =========================================================


router = Router(
    name="settings",
)


# =========================================================
# HELPERS
# =========================================================


def build_settings_keyboard(
    settings,
):
    """
    Build settings keyboard from persisted settings.
    """

    return settings_keyboard(
        bot_enabled=settings.bot_enabled,
        backup_enabled=settings.backup_enabled,
        retention_enabled=settings.retention_enabled,
        retention_keep_last=settings.retention_keep_last,
        compression_level=settings.compression_level,
    )


# =========================================================
# SETTINGS MENU
# =========================================================


@router.callback_query(
    F.data == SETTINGS_CALLBACK,
)
async def settings_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display runtime settings.
    """

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    try:
        settings = context.settings.get_settings()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در دریافت تنظیمات.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        format_settings_menu(
            settings,
        ),
        reply_markup=(build_settings_keyboard(settings)),
    )


# =========================================================
# BOT DISABLE
# =========================================================


@router.callback_query(
    F.data == BOT_DISABLE_CALLBACK,
)
async def disable_bot_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Disable the entire application.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        context.settings.disable_bot()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در غیرفعال کردن ربات.",
            show_alert=True,
        )
        return

    try:
        context.scheduler.pause()

    except Exception:
        logger.exception("Bot was disabled but scheduler pause failed.")

    await callback.answer("ربات غیرفعال شد.")

    await callback.message.edit_text(
        format_bot_disabled(),
        reply_markup=(disabled_bot_keyboard()),
    )


# =========================================================
# BOT ENABLE
# =========================================================


@router.callback_query(
    F.data == BOT_ENABLE_CALLBACK,
)
async def enable_bot_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Re-enable application activity.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        context.settings.enable_bot()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در فعال کردن ربات.",
            show_alert=True,
        )
        return

    scheduler_error = False

    try:
        context.scheduler.resume()

    except Exception:
        scheduler_error = True

        logger.exception("Bot was enabled but scheduler resume failed.")

    if scheduler_error:
        await callback.answer(
            "ربات فعال شد، اما راه‌اندازی " "زمان‌بندی با خطا مواجه شد.",
            show_alert=True,
        )

    else:
        await callback.answer("ربات فعال شد.")

    try:
        text = build_welcome_message(
            context,
        )

    except Exception:
        logger.exception("Could not build main dashboard after enabling bot.")

        settings = context.settings.get_settings()

        await callback.message.edit_text(
            format_settings_menu(
                settings,
            ),
            reply_markup=(build_settings_keyboard(settings)),
        )

        return

    await callback.message.edit_text(
        text,
        reply_markup=(main_menu_keyboard()),
    )


# =========================================================
# BACKUP ENABLE
# =========================================================


@router.callback_query(
    F.data == BACKUP_ENABLE_CALLBACK,
)
async def enable_backups_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Enable global backup functionality.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.enable_backups()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در فعال کردن بکاپ‌ها.",
            show_alert=True,
        )
        return

    await callback.answer("بکاپ‌ها فعال شدند.")

    await callback.message.edit_text(
        format_settings_menu(
            settings,
        ),
        reply_markup=(build_settings_keyboard(settings)),
    )


# =========================================================
# BACKUP DISABLE
# =========================================================


@router.callback_query(
    F.data == BACKUP_DISABLE_CALLBACK,
)
async def disable_backups_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Disable global backup functionality.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.disable_backups()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در غیرفعال کردن بکاپ‌ها.",
            show_alert=True,
        )
        return

    await callback.answer("بکاپ‌ها غیرفعال شدند.")

    await callback.message.edit_text(
        format_settings_menu(
            settings,
        ),
        reply_markup=(build_settings_keyboard(settings)),
    )


# =========================================================
# COMPRESSION MENU
# =========================================================


@router.callback_query(
    F.data == COMPRESSION_LEVEL_CALLBACK,
)
async def compression_level_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display compression-level selection menu.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.get_settings()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در دریافت تنظیمات فشرده‌سازی.",
            show_alert=True,
        )
        return

    await callback.answer()

    await callback.message.edit_text(
        format_compression_level_menu(
            current_level=(settings.compression_level),
        ),
        reply_markup=(
            compression_level_keyboard(
                current_level=(settings.compression_level),
            )
        ),
    )


# =========================================================
# COMPRESSION SET
# =========================================================


@router.callback_query(
    F.data.startswith(COMPRESSION_LEVEL_SET_PREFIX),
)
async def set_compression_level_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Persist selected compression level.
    """

    callback_data = callback.data or ""

    raw_level = callback_data.removeprefix(COMPRESSION_LEVEL_SET_PREFIX)

    try:
        compression_level = int(raw_level)

    except ValueError:
        await callback.answer(
            "سطح فشرده‌سازی نامعتبر است.",
            show_alert=True,
        )
        return

    if not 0 <= compression_level <= 9:
        await callback.answer(
            "سطح فشرده‌سازی باید بین 0 تا 9 باشد.",
            show_alert=True,
        )
        return

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.set_compression_level(
            compression_level,
        )

    except ValidationError:
        await callback.answer(
            "سطح فشرده‌سازی نامعتبر است.",
            show_alert=True,
        )
        return

    except SettingsPersistenceError:
        logger.exception("Could not update compression level.")

        await callback.answer(
            "خطا در ذخیره سطح فشرده‌سازی.",
            show_alert=True,
        )
        return

    await callback.answer("سطح فشرده‌سازی " f"روی {compression_level} تنظیم شد.")

    await callback.message.edit_text(
        format_compression_level_menu(
            current_level=(settings.compression_level),
        ),
        reply_markup=(
            compression_level_keyboard(
                current_level=(settings.compression_level),
            )
        ),
    )


# =========================================================
# RETENTION ENABLE
# =========================================================


@router.callback_query(
    F.data == RETENTION_ENABLE_CALLBACK,
)
async def enable_retention_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Enable automatic backup retention cleanup.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.enable_retention()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در فعال کردن نگهداری بکاپ‌ها.",
            show_alert=True,
        )
        return

    await callback.answer("نگهداری بکاپ‌ها فعال شد.")

    await callback.message.edit_text(
        format_settings_menu(
            settings,
        ),
        reply_markup=(build_settings_keyboard(settings)),
    )


# =========================================================
# RETENTION DISABLE
# =========================================================


@router.callback_query(
    F.data == RETENTION_DISABLE_CALLBACK,
)
async def disable_retention_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Disable automatic backup retention cleanup.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.disable_retention()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در غیرفعال کردن نگهداری بکاپ‌ها.",
            show_alert=True,
        )
        return

    await callback.answer("نگهداری بکاپ‌ها غیرفعال شد.")

    await callback.message.edit_text(
        format_settings_menu(
            settings,
        ),
        reply_markup=(build_settings_keyboard(settings)),
    )


# =========================================================
# RETENTION KEEP-LAST START
# =========================================================


@router.callback_query(
    F.data == RETENTION_KEEP_LAST_CALLBACK,
)
async def retention_keep_last_callback(
    callback: CallbackQuery,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Start retention keep-last update flow.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.get_settings()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در دریافت تنظیمات.",
            show_alert=True,
        )
        return

    await state.set_state(
        SettingsState.waiting_for_retention_keep_last,
    )

    await callback.answer()

    await callback.message.edit_text(
        format_retention_keep_last_prompt(
            current_value=(settings.retention_keep_last),
        ),
        reply_markup=(retention_keep_last_keyboard()),
    )


# =========================================================
# RETENTION KEEP-LAST INPUT
# =========================================================


@router.message(
    SettingsState.waiting_for_retention_keep_last,
)
async def retention_keep_last_handler(
    message: Message,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Persist a new backup retention keep-last value.
    """

    raw_value = (message.text or "").strip()

    try:
        keep_last = int(raw_value)

    except ValueError:
        await message.answer(
            "❌ مقدار واردشده معتبر نیست.\n"
            "\n"
            "لطفاً یک عدد صحیح بزرگ‌تر یا مساوی "
            "با 1 وارد کنید."
        )
        return

    if keep_last < 1:
        await message.answer("❌ تعداد بکاپ‌ها باید حداقل 1 باشد.")
        return

    try:
        settings = context.settings.set_retention_keep_last(
            keep_last,
        )

    except ValidationError:
        await message.answer("❌ مقدار واردشده معتبر نیست.")
        return

    except SettingsPersistenceError:
        logger.exception("Could not update backup retention keep-last.")

        await message.answer("❌ خطا در ذخیره تنظیمات نگهداری بکاپ‌ها.")
        return

    await state.clear()

    await message.answer(
        "✅ تعداد بکاپ‌های نگهداری‌شده "
        f"روی {keep_last} تنظیم شد.\n"
        "\n"
        + format_settings_menu(
            settings,
        ),
        reply_markup=(build_settings_keyboard(settings)),
    )


# =========================================================
# RETENTION KEEP-LAST CANCEL
# =========================================================


@router.callback_query(
    F.data == RETENTION_KEEP_LAST_CANCEL_CALLBACK,
)
async def retention_keep_last_cancel_callback(
    callback: CallbackQuery,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Cancel backup retention keep-last input flow.
    """

    await state.clear()

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.get_settings()

    except SettingsPersistenceError:
        await callback.answer(
            "خطا در دریافت تنظیمات.",
            show_alert=True,
        )
        return

    await callback.answer("تغییر مقدار لغو شد.")

    await callback.message.edit_text(
        format_settings_menu(
            settings,
        ),
        reply_markup=(build_settings_keyboard(settings)),
    )


__all__ = [
    "router",
]
