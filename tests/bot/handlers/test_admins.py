from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram import (
    Bot,
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
from aiogram.methods import (
    SendMessage,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.formatters.admins import (
    AdminDeliveryStatus,
)
from django_assistant_bot.bot.handlers.admins import (
    admin_add_callback,
    admin_cancel_callback,
    admin_delete_callback,
    admin_delete_list_callback,
    admin_user_id_handler,
    admins_menu_callback,
    verify_admin_delivery,
)
from django_assistant_bot.bot.keyboards.admins import (
    ADMIN_ADD_CALLBACK,
    ADMIN_CANCEL_CALLBACK,
    ADMIN_DELETE_PREFIX,
    ADMINS_CALLBACK,
)
from django_assistant_bot.bot.states.admin import (
    AdminManagementState,
)
from django_assistant_bot.schemas.admin import (
    AdminSchema,
)
from django_assistant_bot.services.admin import (
    AdminAlreadyExistsError,
    AdminNotFoundError,
    AdminPersistenceError,
    AdminValidationError,
    LastAdminRemovalError,
)

# =========================================================
# BUILDERS
# =========================================================


def build_admin(
    telegram_user_id: int,
) -> AdminSchema:
    return AdminSchema(
        telegram_user_id=telegram_user_id,
        created_at=datetime.now(
            UTC,
        ),
    )


def build_callback(
    *,
    data: str,
) -> Mock:
    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    callback = Mock(
        spec=CallbackQuery,
    )

    callback.data = data

    callback.message = message

    callback.answer = AsyncMock()

    return callback


def build_message(
    *,
    text: str | None = None,
) -> Mock:
    message = Mock(
        spec=Message,
    )

    message.text = text

    message.answer = AsyncMock()

    return message


def build_state() -> Mock:
    state = Mock(
        spec=FSMContext,
    )

    state.clear = AsyncMock()

    state.set_state = AsyncMock()

    return state


def build_bot() -> Mock:
    bot = Mock(
        spec=Bot,
    )

    bot.send_message = AsyncMock()

    return bot


def build_context(
    *,
    admins: Mock | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(admins=(admins if admins is not None else Mock()))


def build_send_message_method(
    *,
    chat_id: int = 123456789,
) -> SendMessage:
    return SendMessage(
        chat_id=chat_id,
        text="test",
    )


# =========================================================
# DELIVERY VERIFICATION
# =========================================================


@pytest.mark.asyncio
async def test_verify_admin_delivery_success() -> None:
    bot = build_bot()

    result = await verify_admin_delivery(
        bot=bot,
        telegram_user_id=123456789,
    )

    assert result == AdminDeliveryStatus.VERIFIED

    bot.send_message.assert_awaited_once()

    call = bot.send_message.await_args

    assert call.kwargs["chat_id"] == 123456789


@pytest.mark.asyncio
async def test_verify_admin_delivery_blocked() -> None:
    bot = build_bot()

    bot.send_message.side_effect = TelegramForbiddenError(
        method=build_send_message_method(),
        message=("Forbidden: bot was blocked by the user"),
    )

    result = await verify_admin_delivery(
        bot=bot,
        telegram_user_id=123456789,
    )

    assert result == AdminDeliveryStatus.BLOCKED

    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_admin_delivery_chat_unavailable() -> None:
    bot = build_bot()

    bot.send_message.side_effect = TelegramBadRequest(
        method=build_send_message_method(),
        message="Bad Request: chat not found",
    )

    result = await verify_admin_delivery(
        bot=bot,
        telegram_user_id=123456789,
    )

    assert result == AdminDeliveryStatus.CHAT_UNAVAILABLE

    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_admin_delivery_network_failure() -> None:
    bot = build_bot()

    bot.send_message.side_effect = TelegramNetworkError(
        method=build_send_message_method(),
        message="connection reset",
    )

    result = await verify_admin_delivery(
        bot=bot,
        telegram_user_id=123456789,
    )

    assert result == AdminDeliveryStatus.TEMPORARY_FAILURE

    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_admin_delivery_unexpected_api_error() -> None:
    bot = build_bot()

    bot.send_message.side_effect = TelegramAPIError(
        method=build_send_message_method(),
        message="unexpected telegram error",
    )

    result = await verify_admin_delivery(
        bot=bot,
        telegram_user_id=123456789,
    )

    assert result == AdminDeliveryStatus.API_FAILURE

    bot.send_message.assert_awaited_once()


# =========================================================
# MENU
# =========================================================


@pytest.mark.asyncio
async def test_admins_menu_lists_admins() -> None:
    admins = Mock()

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
        build_admin(
            222,
        ),
    ]

    callback = build_callback(
        data=ADMINS_CALLBACK,
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    await admins_menu_callback(
        callback,
        context,
        state,
    )

    state.clear.assert_awaited_once_with()

    admins.list_admins.assert_called_once_with()

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "مدیریت ادمین‌ها" in text

    assert "111" in text

    assert "222" in text

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert ADMIN_ADD_CALLBACK in callbacks

    assert "admin:delete:list" in callbacks

    assert "main:menu" in callbacks


@pytest.mark.asyncio
async def test_admins_menu_handles_persistence_error() -> None:
    admins = Mock()

    admins.list_admins.side_effect = AdminPersistenceError("database unavailable")

    callback = build_callback(
        data=ADMINS_CALLBACK,
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    await admins_menu_callback(
        callback,
        context,
        state,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در دریافت لیست ادمین‌ها.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# ADD FLOW
# =========================================================


@pytest.mark.asyncio
async def test_admin_add_callback_starts_state() -> None:
    callback = build_callback(
        data=ADMIN_ADD_CALLBACK,
    )

    state = build_state()

    await admin_add_callback(
        callback,
        state,
    )

    state.clear.assert_awaited_once_with()

    state.set_state.assert_awaited_once_with(
        AdminManagementState.waiting_for_user_id,
    )

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "افزودن ادمین" in text

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert callbacks == [
        ADMIN_CANCEL_CALLBACK,
    ]


@pytest.mark.asyncio
async def test_admin_user_id_handler_rejects_empty_input() -> None:
    message = build_message(
        text="   ",
    )

    state = build_state()

    context = build_context()

    bot = build_bot()

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    message.answer.assert_awaited_once_with("❌ Telegram ID نمی‌تواند خالی باشد.")

    state.clear.assert_not_awaited()

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_user_id_handler_rejects_non_numeric_input() -> None:
    message = build_message(
        text="abc123",
    )

    state = build_state()

    context = build_context()

    bot = build_bot()

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    message.answer.assert_awaited_once_with("❌ Telegram ID باید فقط شامل عدد باشد.")

    state.clear.assert_not_awaited()

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_user_id_handler_adds_verified_admin() -> None:
    admins = Mock()

    created_admin = build_admin(
        123456789,
    )

    admins.add_admin.return_value = created_admin

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
        created_admin,
    ]

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    bot = build_bot()

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    admins.add_admin.assert_called_once_with(
        123456789,
    )

    bot.send_message.assert_awaited_once()

    state.clear.assert_awaited_once_with()

    admins.list_admins.assert_called_once_with()

    message.answer.assert_awaited_once()

    call = message.answer.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "ادمین اضافه شد" in text

    assert "123456789" in text

    assert "ارتباط با تلگرام تأیید شد" in text

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert ADMIN_ADD_CALLBACK in callbacks

    assert "admin:delete:list" in callbacks


@pytest.mark.asyncio
async def test_admin_creation_survives_blocked_user() -> None:
    admins = Mock()

    created_admin = build_admin(
        123456789,
    )

    admins.add_admin.return_value = created_admin

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
        created_admin,
    ]

    bot = build_bot()

    bot.send_message.side_effect = TelegramForbiddenError(
        method=build_send_message_method(),
        message=("Forbidden: bot was blocked by the user"),
    )

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    admins.add_admin.assert_called_once_with(
        123456789,
    )

    state.clear.assert_awaited_once_with()

    admins.list_admins.assert_called_once_with()

    message.answer.assert_awaited_once()

    text = message.answer.await_args.args[0]

    assert "ادمین اضافه شد" in text

    assert "ربات توسط این کاربر Block شده" in text

    assert "Unblock" in text

    assert "/start" in text


@pytest.mark.asyncio
async def test_admin_creation_survives_chat_unavailable() -> None:
    admins = Mock()

    created_admin = build_admin(
        123456789,
    )

    admins.add_admin.return_value = created_admin

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
        created_admin,
    ]

    bot = build_bot()

    bot.send_message.side_effect = TelegramBadRequest(
        method=build_send_message_method(),
        message="Bad Request: chat not found",
    )

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    state.clear.assert_awaited_once_with()

    message.answer.assert_awaited_once()

    text = message.answer.await_args.args[0]

    assert "ادمین اضافه شد" in text

    assert "گفتگو با این کاربر هنوز در دسترس نیست" in text

    assert "/start" in text


@pytest.mark.asyncio
async def test_admin_creation_survives_network_failure() -> None:
    admins = Mock()

    created_admin = build_admin(
        123456789,
    )

    admins.add_admin.return_value = created_admin

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
        created_admin,
    ]

    bot = build_bot()

    bot.send_message.side_effect = TelegramNetworkError(
        method=build_send_message_method(),
        message="connection reset",
    )

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    state.clear.assert_awaited_once_with()

    message.answer.assert_awaited_once()

    text = message.answer.await_args.args[0]

    assert "ادمین اضافه شد" in text

    assert "بررسی ارتباط موقتاً ناموفق بود" in text


@pytest.mark.asyncio
async def test_admin_user_id_handler_handles_duplicate() -> None:
    admins = Mock()

    admins.add_admin.side_effect = AdminAlreadyExistsError("already exists")

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    bot = build_bot()

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    message.answer.assert_awaited_once_with("⚠️ این کاربر از قبل ادمین است.")

    state.clear.assert_not_awaited()

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_user_id_handler_handles_validation_error() -> None:
    admins = Mock()

    admins.add_admin.side_effect = AdminValidationError("invalid")

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    bot = build_bot()

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    message.answer.assert_awaited_once_with("❌ Telegram ID نامعتبر است.")

    state.clear.assert_not_awaited()

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_user_id_handler_handles_persistence_error() -> None:
    admins = Mock()

    admins.add_admin.side_effect = AdminPersistenceError("database unavailable")

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    bot = build_bot()

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    message.answer.assert_awaited_once_with("❌ خطایی هنگام ذخیره ادمین رخ داد.")

    state.clear.assert_not_awaited()

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_user_id_handler_survives_reload_failure() -> None:
    admins = Mock()

    created_admin = build_admin(
        123456789,
    )

    admins.add_admin.return_value = created_admin

    admins.list_admins.side_effect = AdminPersistenceError("database unavailable")

    message = build_message(
        text="123456789",
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    bot = build_bot()

    await admin_user_id_handler(
        message,
        state,
        context,
        bot,
    )

    admins.add_admin.assert_called_once_with(
        123456789,
    )

    bot.send_message.assert_awaited_once()

    state.clear.assert_awaited_once_with()

    message.answer.assert_awaited_once()

    text = message.answer.await_args.args[0]

    assert "ادمین اضافه شد" in text

    assert "123456789" in text

    assert "ارتباط با تلگرام تأیید شد" in text


# =========================================================
# DELETE LIST
# =========================================================


@pytest.mark.asyncio
async def test_admin_delete_list_displays_admins() -> None:
    admins = Mock()

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
        build_admin(
            222,
        ),
    ]

    callback = build_callback(
        data="admin:delete:list",
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_list_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "حذف ادمین" in text

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert f"{ADMIN_DELETE_PREFIX}111" in callbacks

    assert f"{ADMIN_DELETE_PREFIX}222" in callbacks

    assert ADMINS_CALLBACK in callbacks


@pytest.mark.asyncio
async def test_admin_delete_list_blocks_last_admin() -> None:
    admins = Mock()

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
    ]

    callback = build_callback(
        data="admin:delete:list",
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_list_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "آخرین ادمین قابل حذف نیست.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_delete_list_handles_persistence_error() -> None:
    admins = Mock()

    admins.list_admins.side_effect = AdminPersistenceError("database unavailable")

    callback = build_callback(
        data="admin:delete:list",
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_list_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در دریافت لیست ادمین‌ها.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# DELETE
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "callback_data",
    [
        "admin:delete:",
        "admin:delete:abc",
        "admin:delete:-1",
    ],
)
async def test_admin_delete_rejects_invalid_callback(
    callback_data: str,
) -> None:
    callback = build_callback(
        data=callback_data,
    )

    context = build_context()

    await admin_delete_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "شناسه ادمین نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_delete_removes_admin() -> None:
    admins = Mock()

    admins.list_admins.return_value = [
        build_admin(
            222,
        ),
    ]

    callback = build_callback(
        data=(f"{ADMIN_DELETE_PREFIX}" "111"),
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_callback(
        callback,
        context,
    )

    admins.remove_admin.assert_called_once_with(
        111,
    )

    admins.list_admins.assert_called_once_with()

    callback.answer.assert_awaited_once_with("ادمین حذف شد.")

    callback.message.edit_text.assert_awaited_once()

    text = callback.message.edit_text.await_args.args[0]

    assert "ادمین حذف شد" in text

    assert "111" in text

    assert "222" in text


@pytest.mark.asyncio
async def test_admin_delete_blocks_last_admin() -> None:
    admins = Mock()

    admins.remove_admin.side_effect = LastAdminRemovalError("last admin")

    callback = build_callback(
        data=(f"{ADMIN_DELETE_PREFIX}" "111"),
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "آخرین ادمین قابل حذف نیست.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_delete_handles_not_found() -> None:
    admins = Mock()

    admins.remove_admin.side_effect = AdminNotFoundError("not found")

    callback = build_callback(
        data=(f"{ADMIN_DELETE_PREFIX}" "111"),
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "ادمین موردنظر پیدا نشد.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_delete_handles_validation_error() -> None:
    admins = Mock()

    admins.remove_admin.side_effect = AdminValidationError("invalid")

    callback = build_callback(
        data=(f"{ADMIN_DELETE_PREFIX}" "111"),
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "شناسه ادمین نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_delete_handles_persistence_error() -> None:
    admins = Mock()

    admins.remove_admin.side_effect = AdminPersistenceError("database unavailable")

    callback = build_callback(
        data=(f"{ADMIN_DELETE_PREFIX}" "111"),
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در حذف ادمین.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_delete_survives_reload_failure() -> None:
    admins = Mock()

    admins.list_admins.side_effect = AdminPersistenceError("database unavailable")

    callback = build_callback(
        data=(f"{ADMIN_DELETE_PREFIX}" "111"),
    )

    context = build_context(
        admins=admins,
    )

    await admin_delete_callback(
        callback,
        context,
    )

    admins.remove_admin.assert_called_once_with(
        111,
    )

    callback.answer.assert_awaited_once_with("ادمین حذف شد.")

    callback.message.edit_text.assert_awaited_once()

    text = callback.message.edit_text.await_args.args[0]

    assert "ادمین حذف شد" in text

    assert "111" in text


# =========================================================
# CANCEL
# =========================================================


@pytest.mark.asyncio
async def test_admin_cancel_returns_to_admin_menu() -> None:
    admins = Mock()

    admins.list_admins.return_value = [
        build_admin(
            111,
        ),
    ]

    callback = build_callback(
        data=ADMIN_CANCEL_CALLBACK,
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    await admin_cancel_callback(
        callback,
        context,
        state,
    )

    state.clear.assert_awaited_once_with()

    admins.list_admins.assert_called_once_with()

    callback.answer.assert_awaited_once_with("عملیات لغو شد.")

    callback.message.edit_text.assert_awaited_once()

    text = callback.message.edit_text.await_args.args[0]

    assert "مدیریت ادمین‌ها" in text


@pytest.mark.asyncio
async def test_admin_cancel_handles_persistence_error() -> None:
    admins = Mock()

    admins.list_admins.side_effect = AdminPersistenceError("database unavailable")

    callback = build_callback(
        data=ADMIN_CANCEL_CALLBACK,
    )

    state = build_state()

    context = build_context(
        admins=admins,
    )

    await admin_cancel_callback(
        callback,
        context,
        state,
    )

    state.clear.assert_awaited_once_with()

    callback.answer.assert_awaited_once_with(
        "خطا در دریافت لیست ادمین‌ها.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()
