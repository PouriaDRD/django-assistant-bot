from __future__ import annotations

import logging

from aiogram import (
    Bot,
    F,
    Router,
)
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
)
from aiogram.fsm.context import (
    FSMContext,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.admins import (
    AdminDeliveryStatus,
    format_add_admin_prompt,
    format_admin_created,
    format_admin_removed,
    format_admin_welcome,
    format_admins_menu,
)
from django_assistant_bot.bot.keyboards.admins import (
    ADMIN_ADD_CALLBACK,
    ADMIN_CANCEL_CALLBACK,
    ADMIN_DELETE_PREFIX,
    ADMINS_CALLBACK,
    admin_creation_keyboard,
    admin_delete_keyboard,
    admins_menu_keyboard,
)
from django_assistant_bot.bot.states.admin import (
    AdminManagementState,
)
from django_assistant_bot.services.admin import (
    AdminAlreadyExistsError,
    AdminNotFoundError,
    AdminPersistenceError,
    AdminValidationError,
    LastAdminRemovalError,
)

logger = logging.getLogger(
    __name__,
)


router = Router(
    name="admins",
)


# =========================================================
# HELPERS
# =========================================================


async def verify_admin_delivery(
    *,
    bot: Bot,
    telegram_user_id: int,
) -> AdminDeliveryStatus:
    """
    Verify Telegram delivery access for a newly created
    administrator.

    Expected Telegram delivery failures are handled without
    noisy tracebacks.

    Verification failure never rolls back administrator
    creation.
    """

    try:
        await bot.send_message(
            chat_id=telegram_user_id,
            text=format_admin_welcome(),
        )

    except TelegramForbiddenError as exc:
        logger.warning(
            (
                "Telegram delivery verification failed for "
                "admin %s: user blocked the bot. message=%s"
            ),
            telegram_user_id,
            exc.message,
        )

        return AdminDeliveryStatus.BLOCKED

    except TelegramBadRequest as exc:
        logger.warning(
            (
                "Telegram delivery verification failed for "
                "admin %s: chat unavailable. message=%s"
            ),
            telegram_user_id,
            exc.message,
        )

        return AdminDeliveryStatus.CHAT_UNAVAILABLE

    except TelegramNetworkError as exc:
        logger.warning(
            (
                "Telegram delivery verification temporarily "
                "failed for admin %s due to network error: %s"
            ),
            telegram_user_id,
            exc,
        )

        return AdminDeliveryStatus.TEMPORARY_FAILURE

    except TelegramAPIError:
        logger.exception(
            ("Unexpected Telegram API error while verifying " "delivery for admin %s."),
            telegram_user_id,
        )

        return AdminDeliveryStatus.API_FAILURE

    logger.info(
        ("Telegram delivery verified successfully for " "admin %s."),
        telegram_user_id,
    )

    return AdminDeliveryStatus.VERIFIED


# =========================================================
# MENU
# =========================================================


@router.callback_query(
    F.data == ADMINS_CALLBACK,
)
async def admins_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
    state: FSMContext,
) -> None:
    """
    Display administrator management menu.
    """

    await state.clear()

    try:
        admins = context.admins.list_admins()

    except AdminPersistenceError:
        logger.exception("Could not load administrators.")

        await callback.answer(
            "خطا در دریافت لیست ادمین‌ها.",
            show_alert=True,
        )

        return

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_admins_menu(
            admins,
        ),
        reply_markup=admins_menu_keyboard(
            admins,
        ),
    )


# =========================================================
# ADD
# =========================================================


@router.callback_query(
    F.data == ADMIN_ADD_CALLBACK,
)
async def admin_add_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Start administrator creation flow.
    """

    await state.clear()

    await state.set_state(
        AdminManagementState.waiting_for_user_id,
    )

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_add_admin_prompt(),
        reply_markup=admin_creation_keyboard(),
    )


@router.message(
    AdminManagementState.waiting_for_user_id,
)
async def admin_user_id_handler(
    message: Message,
    state: FSMContext,
    context: ApplicationContext,
    bot: Bot,
) -> None:
    """
    Validate and persist administrator Telegram ID.

    After persistence, verify that Telegram can deliver
    messages to the newly registered administrator.
    """

    raw_user_id = (message.text or "").strip()

    if not raw_user_id:
        await message.answer("❌ Telegram ID نمی‌تواند خالی باشد.")

        return

    if not raw_user_id.isdigit():
        await message.answer("❌ Telegram ID باید فقط شامل عدد باشد.")

        return

    telegram_user_id = int(raw_user_id)

    try:
        admin = context.admins.add_admin(
            telegram_user_id,
        )

    except AdminAlreadyExistsError:
        await message.answer("⚠️ این کاربر از قبل ادمین است.")

        return

    except AdminValidationError:
        await message.answer("❌ Telegram ID نامعتبر است.")

        return

    except AdminPersistenceError:
        logger.exception("Could not create administrator.")

        await message.answer("❌ خطایی هنگام ذخیره ادمین رخ داد.")

        return

    # -----------------------------------------------------
    # TELEGRAM DELIVERY VERIFICATION
    # -----------------------------------------------------

    delivery_status = await verify_admin_delivery(
        bot=bot,
        telegram_user_id=(admin.telegram_user_id),
    )

    await state.clear()

    try:
        admins = context.admins.list_admins()

    except AdminPersistenceError:
        logger.exception(
            ("Administrator was created but " "could not reload admin list.")
        )

        await message.answer(
            format_admin_created(
                admin.telegram_user_id,
                delivery_status=(delivery_status),
            )
        )

        return

    await message.answer(
        (
            format_admin_created(
                admin.telegram_user_id,
                delivery_status=(delivery_status),
            )
            + "\n\n"
            + format_admins_menu(
                admins,
            )
        ),
        reply_markup=admins_menu_keyboard(
            admins,
        ),
    )


# =========================================================
# DELETE LIST
# =========================================================


@router.callback_query(
    F.data == "admin:delete:list",
)
async def admin_delete_list_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display administrators available for deletion.
    """

    try:
        admins = context.admins.list_admins()

    except AdminPersistenceError:
        logger.exception("Could not load administrators.")

        await callback.answer(
            "خطا در دریافت لیست ادمین‌ها.",
            show_alert=True,
        )

        return

    if len(admins) <= 1:
        await callback.answer(
            "آخرین ادمین قابل حذف نیست.",
            show_alert=True,
        )

        return

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        ("➖ <b>حذف ادمین</b>\n" "\n" "ادمینی که می‌خواهید حذف شود " "را انتخاب کنید."),
        reply_markup=admin_delete_keyboard(
            admins,
        ),
    )


# =========================================================
# DELETE
# =========================================================


@router.callback_query(
    F.data.startswith(ADMIN_DELETE_PREFIX),
)
async def admin_delete_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Remove selected administrator.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()

        return

    raw_user_id = callback_data.removeprefix(ADMIN_DELETE_PREFIX)

    if not raw_user_id or not raw_user_id.isdigit():
        await callback.answer(
            "شناسه ادمین نامعتبر است.",
            show_alert=True,
        )

        return

    telegram_user_id = int(raw_user_id)

    try:
        context.admins.remove_admin(
            telegram_user_id,
        )

    except LastAdminRemovalError:
        await callback.answer(
            "آخرین ادمین قابل حذف نیست.",
            show_alert=True,
        )

        return

    except AdminNotFoundError:
        await callback.answer(
            "ادمین موردنظر پیدا نشد.",
            show_alert=True,
        )

        return

    except AdminValidationError:
        await callback.answer(
            "شناسه ادمین نامعتبر است.",
            show_alert=True,
        )

        return

    except AdminPersistenceError:
        logger.exception("Could not remove administrator.")

        await callback.answer(
            "خطا در حذف ادمین.",
            show_alert=True,
        )

        return

    try:
        admins = context.admins.list_admins()

    except AdminPersistenceError:
        logger.exception(("Administrator removed but " "could not reload admin list."))

        await callback.answer("ادمین حذف شد.")

        if isinstance(
            callback.message,
            Message,
        ):
            await callback.message.edit_text(
                format_admin_removed(
                    telegram_user_id,
                )
            )

        return

    await callback.answer("ادمین حذف شد.")

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        (
            format_admin_removed(
                telegram_user_id,
            )
            + "\n\n"
            + format_admins_menu(
                admins,
            )
        ),
        reply_markup=admins_menu_keyboard(
            admins,
        ),
    )


# =========================================================
# CANCEL
# =========================================================


@router.callback_query(
    F.data == ADMIN_CANCEL_CALLBACK,
)
async def admin_cancel_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
    state: FSMContext,
) -> None:
    """
    Cancel administrator creation flow.
    """

    await state.clear()

    try:
        admins = context.admins.list_admins()

    except AdminPersistenceError:
        logger.exception("Could not load administrators.")

        await callback.answer(
            "خطا در دریافت لیست ادمین‌ها.",
            show_alert=True,
        )

        return

    await callback.answer("عملیات لغو شد.")

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_admins_menu(
            admins,
        ),
        reply_markup=admins_menu_keyboard(
            admins,
        ),
    )


__all__ = [
    "router",
    "verify_admin_delivery",
]
