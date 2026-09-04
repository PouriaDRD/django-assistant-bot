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
from pydantic import (
    ValidationError,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.proxy import (
    format_proxy_menu,
    format_proxy_test_result,
    format_proxy_url_prompt,
)
from django_assistant_bot.bot.keyboards.proxy import (
    PROXY_CALLBACK,
    PROXY_CANCEL_CALLBACK,
    PROXY_CLEAR_CALLBACK,
    PROXY_DISABLE_CALLBACK,
    PROXY_ENABLE_CALLBACK,
    PROXY_SET_URL_CALLBACK,
    PROXY_TEST_CALLBACK,
    proxy_keyboard,
    proxy_url_input_keyboard,
)
from django_assistant_bot.bot.proxy_connection import (
    ProxyConnectionTestResult,
    check_telegram_proxy_connection,
)
from django_assistant_bot.bot.states.proxy import (
    ProxyState,
)
from django_assistant_bot.services.settings import (
    ProxyConfigurationError,
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
    name="proxy",
)


# =========================================================
# HELPERS
# =========================================================


async def check_configured_proxy(
    context: ApplicationContext,
) -> ProxyConnectionTestResult:
    """
    Check the currently configured proxy against Telegram.

    A temporary Telegram HTTP session is used.

    The application's active polling session is never
    modified.
    """

    settings = context.settings.get_settings()

    if not settings.proxy_url:
        raise ProxyConfigurationError("Proxy URL is not configured.")

    token = context.environment.telegram_bot_token.get_secret_value()

    return await check_telegram_proxy_connection(
        token=token,
        proxy_url=settings.proxy_url,
    )


# =========================================================
# PROXY MENU
# =========================================================


@router.callback_query(
    F.data == PROXY_CALLBACK,
)
async def proxy_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display proxy management menu.
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
            "خطا در دریافت تنظیمات پروکسی.",
            show_alert=True,
        )
        return

    await callback.answer()

    await callback.message.edit_text(
        format_proxy_menu(
            settings,
        ),
        reply_markup=(
            proxy_keyboard(
                proxy_enabled=(settings.proxy_enabled),
                has_proxy_url=bool(settings.proxy_url),
            )
        ),
    )


# =========================================================
# SET PROXY URL
# =========================================================


@router.callback_query(
    F.data == PROXY_SET_URL_CALLBACK,
)
async def proxy_set_url_callback(
    callback: CallbackQuery,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Start proxy URL input flow.
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
            "خطا در دریافت تنظیمات پروکسی.",
            show_alert=True,
        )
        return

    await state.set_state(
        ProxyState.waiting_for_proxy_url,
    )

    await callback.answer()

    await callback.message.edit_text(
        format_proxy_url_prompt(
            settings,
        ),
        reply_markup=(proxy_url_input_keyboard()),
    )


# =========================================================
# PROXY URL INPUT
# =========================================================


@router.message(
    ProxyState.waiting_for_proxy_url,
)
async def proxy_url_handler(
    message: Message,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Validate and persist proxy URL.
    """

    proxy_url = (message.text or "").strip()

    if not proxy_url:
        await message.answer(("❌ آدرس پروکسی نمی‌تواند " "خالی باشد."))
        return

    try:
        settings = context.settings.set_proxy_url(
            proxy_url,
        )

    except ValidationError:
        await message.answer(
            (
                "❌ آدرس پروکسی معتبر نیست.\n"
                "\n"
                "فرمت‌های قابل قبول:\n"
                "<code>http://host:port</code>\n"
                "<code>socks4://host:port</code>\n"
                "<code>socks5://host:port</code>"
            )
        )
        return

    except SettingsPersistenceError:
        logger.exception("Could not persist proxy URL.")

        await message.answer(("❌ خطا در ذخیره تنظیمات " "پروکسی."))
        return

    await state.clear()

    await message.answer(
        (
            "✅ آدرس پروکسی ذخیره شد.\n"
            "\n"
            "پیشنهاد می‌شود قبل از فعال‌سازی، "
            "اتصال آن را تست کنید.\n"
            "\n"
            + format_proxy_menu(
                settings,
            )
        ),
        reply_markup=(
            proxy_keyboard(
                proxy_enabled=(settings.proxy_enabled),
                has_proxy_url=True,
            )
        ),
    )


# =========================================================
# TEST CONNECTION
# =========================================================


@router.callback_query(
    F.data == PROXY_TEST_CALLBACK,
)
async def proxy_test_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Test configured proxy against Telegram Bot API.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    # Answer immediately so Telegram does not keep
    # the callback in a pending/loading state while the
    # network connection test is running.
    await callback.answer("در حال تست اتصال پروکسی...")

    try:
        settings = context.settings.get_settings()

        if not settings.proxy_url:
            await callback.message.answer(("❌ ابتدا یک آدرس پروکسی " "تنظیم کنید."))
            return

        result = await check_configured_proxy(
            context,
        )

    except ProxyConfigurationError:
        await callback.message.answer(("❌ ابتدا یک آدرس پروکسی " "تنظیم کنید."))
        return

    except SettingsPersistenceError:
        logger.exception(("Could not load proxy settings " "for connection test."))

        await callback.message.answer(("❌ خطا در دریافت تنظیمات " "پروکسی."))
        return

    await callback.message.edit_text(
        (
            format_proxy_test_result(
                result,
            )
            + "\n\n"
            + format_proxy_menu(
                settings,
            )
        ),
        reply_markup=(
            proxy_keyboard(
                proxy_enabled=(settings.proxy_enabled),
                has_proxy_url=True,
            )
        ),
    )


# =========================================================
# ENABLE PROXY
# =========================================================


@router.callback_query(
    F.data == PROXY_ENABLE_CALLBACK,
)
async def proxy_enable_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Test and enable configured proxy.

    The proxy is enabled only after Telegram connectivity
    through that proxy has been verified successfully.

    This reduces the risk of locking the application out
    after restart because of an invalid or inaccessible
    proxy.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    await callback.answer("در حال بررسی پروکسی...")

    try:
        settings = context.settings.get_settings()

        if not settings.proxy_url:
            await callback.message.answer(
                ("❌ ابتدا یک آدرس پروکسی " "معتبر تنظیم کنید.")
            )
            return

        test_result = await check_configured_proxy(
            context,
        )

    except ProxyConfigurationError:
        await callback.message.answer(("❌ ابتدا یک آدرس پروکسی " "معتبر تنظیم کنید."))
        return

    except SettingsPersistenceError:
        logger.exception(("Could not load proxy settings " "before enabling."))

        await callback.message.answer(("❌ خطا در دریافت تنظیمات " "پروکسی."))
        return

    # -----------------------------------------------------
    # CONNECTION FAILED
    # -----------------------------------------------------

    if not test_result.is_successful:
        await callback.message.edit_text(
            (
                format_proxy_test_result(
                    test_result,
                )
                + "\n\n"
                "⛔ پروکسی فعال نشد."
                "\n\n"
                + format_proxy_menu(
                    settings,
                )
            ),
            reply_markup=(
                proxy_keyboard(
                    proxy_enabled=False,
                    has_proxy_url=True,
                )
            ),
        )
        return

    # -----------------------------------------------------
    # CONNECTION SUCCESSFUL
    # -----------------------------------------------------

    try:
        updated_settings = context.settings.enable_proxy()

    except ProxyConfigurationError:
        await callback.message.answer(("❌ امکان فعال‌سازی " "پروکسی وجود ندارد."))
        return

    except SettingsPersistenceError:
        logger.exception("Could not enable proxy.")

        await callback.message.answer(
            (
                "❌ اتصال پروکسی موفق بود، "
                "اما ذخیره وضعیت فعال‌سازی "
                "با خطا مواجه شد."
            )
        )
        return

    await callback.message.edit_text(
        (
            "✅ <b>پروکسی با موفقیت تست و "
            "فعال شد</b>\n"
            "\n"
            "برای اعمال پروکسی روی ارتباط "
            "اصلی ربات، برنامه را مجدداً "
            "راه‌اندازی کنید.\n"
            "\n"
            + format_proxy_menu(
                updated_settings,
            )
        ),
        reply_markup=(
            proxy_keyboard(
                proxy_enabled=True,
                has_proxy_url=True,
            )
        ),
    )


# =========================================================
# DISABLE PROXY
# =========================================================


@router.callback_query(
    F.data == PROXY_DISABLE_CALLBACK,
)
async def proxy_disable_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Disable proxy without deleting its URL.

    The currently running Telegram HTTP session is not
    changed until application restart.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.disable_proxy()

    except SettingsPersistenceError:
        logger.exception("Could not disable proxy.")

        await callback.answer(
            "خطا در غیرفعال کردن پروکسی.",
            show_alert=True,
        )
        return

    await callback.answer("پروکسی غیرفعال شد.")

    await callback.message.edit_text(
        format_proxy_menu(
            settings,
        ),
        reply_markup=(
            proxy_keyboard(
                proxy_enabled=False,
                has_proxy_url=bool(settings.proxy_url),
            )
        ),
    )


# =========================================================
# CLEAR PROXY
# =========================================================


@router.callback_query(
    F.data == PROXY_CLEAR_CALLBACK,
)
async def proxy_clear_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Disable proxy and remove configured URL.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        await callback.answer()
        return

    try:
        settings = context.settings.clear_proxy()

    except SettingsPersistenceError:
        logger.exception("Could not clear proxy settings.")

        await callback.answer(
            "خطا در حذف تنظیمات پروکسی.",
            show_alert=True,
        )
        return

    await callback.answer("پروکسی حذف شد.")

    await callback.message.edit_text(
        format_proxy_menu(
            settings,
        ),
        reply_markup=(
            proxy_keyboard(
                proxy_enabled=False,
                has_proxy_url=False,
            )
        ),
    )


# =========================================================
# CANCEL
# =========================================================


@router.callback_query(
    F.data == PROXY_CANCEL_CALLBACK,
)
async def proxy_cancel_callback(
    callback: CallbackQuery,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Cancel proxy URL input flow.
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
            "خطا در دریافت تنظیمات پروکسی.",
            show_alert=True,
        )
        return

    await callback.answer("تغییر پروکسی لغو شد.")

    await callback.message.edit_text(
        format_proxy_menu(
            settings,
        ),
        reply_markup=(
            proxy_keyboard(
                proxy_enabled=(settings.proxy_enabled),
                has_proxy_url=bool(settings.proxy_url),
            )
        ),
    )


# =========================================================
# EXPORTS
# =========================================================


__all__ = [
    "check_configured_proxy",
    "proxy_cancel_callback",
    "proxy_clear_callback",
    "proxy_disable_callback",
    "proxy_enable_callback",
    "proxy_menu_callback",
    "proxy_set_url_callback",
    "proxy_test_callback",
    "proxy_url_handler",
    "router",
]
