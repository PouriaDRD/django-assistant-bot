from __future__ import annotations

import logging

from aiogram import (
    F,
    Router,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.settings import (
    format_bot_disabled,
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
    SETTINGS_CALLBACK,
    disabled_bot_keyboard,
    settings_keyboard,
)
from django_assistant_bot.services.settings import (
    SettingsPersistenceError,
)

logger = logging.getLogger(
    __name__,
)


router = Router(
    name="settings",
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
        reply_markup=settings_keyboard(
            bot_enabled=(settings.bot_enabled),
            backup_enabled=(settings.backup_enabled),
        ),
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

    Telegram polling remains alive so the bot can be
    re-enabled later.
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

    # Persistence is the source of truth. Even if pausing
    # APScheduler fails, BackupCoordinator still prevents
    # every backup while bot_enabled=False.
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

    This callback is explicitly allowed by
    BotEnabledMiddleware while the bot is disabled.
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
            ("ربات فعال شد، اما راه‌اندازی " "زمان‌بندی با خطا مواجه شد."),
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
            reply_markup=settings_keyboard(
                bot_enabled=(settings.bot_enabled),
                backup_enabled=(settings.backup_enabled),
            ),
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
        reply_markup=settings_keyboard(
            bot_enabled=(settings.bot_enabled),
            backup_enabled=(settings.backup_enabled),
        ),
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
        reply_markup=settings_keyboard(
            bot_enabled=(settings.bot_enabled),
            backup_enabled=(settings.backup_enabled),
        ),
    )


__all__ = [
    "router",
]
