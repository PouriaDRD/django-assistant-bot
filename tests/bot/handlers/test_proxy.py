from __future__ import annotations

from types import SimpleNamespace
from typing import (
    cast,
)
from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)

import pytest
from aiogram.fsm.context import (
    FSMContext,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)
from pydantic import (
    SecretStr,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.handlers.proxy import (
    proxy_cancel_callback,
    proxy_clear_callback,
    proxy_disable_callback,
    proxy_enable_callback,
    proxy_menu_callback,
    proxy_set_url_callback,
    proxy_test_callback,
    proxy_url_handler,
)
from django_assistant_bot.bot.proxy_connection import (
    ProxyConnectionStatus,
    ProxyConnectionTestResult,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# TEST DOUBLE
# =========================================================


class ProxyContextDouble:
    """
    Minimal ApplicationContext test double for proxy
    Telegram handler tests.
    """

    def __init__(
        self,
        settings: AppSettingsSchema,
    ) -> None:
        self.settings = Mock()

        self.settings.get_settings.return_value = settings

        self.settings.set_proxy_url.side_effect = lambda proxy_url: (
            settings.model_copy(
                update={
                    "proxy_enabled": False,
                    "proxy_url": proxy_url,
                },
            )
        )

        self.settings.enable_proxy.return_value = settings.model_copy(
            update={
                "proxy_enabled": True,
            },
        )

        self.settings.disable_proxy.return_value = settings.model_copy(
            update={
                "proxy_enabled": False,
            },
        )

        self.settings.clear_proxy.return_value = settings.model_copy(
            update={
                "proxy_enabled": False,
                "proxy_url": "",
            },
        )

        environment = SimpleNamespace(
            telegram_bot_token=SecretStr(
                "123:test-token",
            ),
        )

        self.context = cast(
            ApplicationContext,
            SimpleNamespace(
                settings=self.settings,
                environment=environment,
            ),
        )


# =========================================================
# MESSAGE / CALLBACK BUILDERS
# =========================================================


def build_message() -> Message:
    message = cast(
        Message,
        Mock(
            spec=Message,
        ),
    )

    setattr(
        message,
        "answer",
        AsyncMock(),
    )

    setattr(
        message,
        "edit_text",
        AsyncMock(),
    )

    return message


def build_callback(
    message: Message,
) -> CallbackQuery:
    callback = cast(
        CallbackQuery,
        Mock(
            spec=CallbackQuery,
        ),
    )

    setattr(
        callback,
        "answer",
        AsyncMock(),
    )

    setattr(
        callback,
        "message",
        message,
    )

    return callback


def build_state() -> FSMContext:
    state = cast(
        FSMContext,
        Mock(
            spec=FSMContext,
        ),
    )

    setattr(
        state,
        "set_state",
        AsyncMock(),
    )

    setattr(
        state,
        "clear",
        AsyncMock(),
    )

    return state


# =========================================================
# ASYNC MOCK ACCESSORS
# =========================================================


def get_answer(
    message: Message,
) -> AsyncMock:
    return cast(
        AsyncMock,
        message.answer,
    )


def get_edit_text(
    message: Message,
) -> AsyncMock:
    return cast(
        AsyncMock,
        message.edit_text,
    )


def get_callback_answer(
    callback: CallbackQuery,
) -> AsyncMock:
    return cast(
        AsyncMock,
        callback.answer,
    )


def get_state_set_state(
    state: FSMContext,
) -> AsyncMock:
    return cast(
        AsyncMock,
        state.set_state,
    )


def get_state_clear(
    state: FSMContext,
) -> AsyncMock:
    return cast(
        AsyncMock,
        state.clear,
    )


def get_awaited_first_argument(
    mock: AsyncMock,
) -> str:
    """
    Return the first positional argument from the latest
    awaited AsyncMock call.

    Explicit assertions make the access safe for both
    runtime and static type checking.
    """

    await_args = mock.await_args

    assert await_args is not None
    assert await_args.args

    return cast(
        str,
        await_args.args[0],
    )


# =========================================================
# MENU
# =========================================================


@pytest.mark.asyncio
async def test_proxy_menu_opens() -> None:
    settings = AppSettingsSchema()

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    await proxy_menu_callback(
        callback,
        double.context,
    )

    double.settings.get_settings.assert_called_once_with()

    get_callback_answer(
        callback,
    ).assert_awaited_once_with()

    get_edit_text(
        message,
    ).assert_awaited_once()


# =========================================================
# SET URL FLOW
# =========================================================


@pytest.mark.asyncio
async def test_proxy_set_url_starts_state() -> None:
    settings = AppSettingsSchema()

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    state = build_state()

    await proxy_set_url_callback(
        callback,
        state,
        double.context,
    )

    get_state_set_state(
        state,
    ).assert_awaited_once()

    get_callback_answer(
        callback,
    ).assert_awaited_once_with()

    get_edit_text(
        message,
    ).assert_awaited_once()


# =========================================================
# SAVE URL
# =========================================================


@pytest.mark.asyncio
async def test_proxy_url_is_saved() -> None:
    settings = AppSettingsSchema()

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    setattr(
        message,
        "text",
        "socks5://127.0.0.1:1080",
    )

    state = build_state()

    await proxy_url_handler(
        message,
        state,
        double.context,
    )

    double.settings.set_proxy_url.assert_called_once_with(
        "socks5://127.0.0.1:1080",
    )

    get_state_clear(
        state,
    ).assert_awaited_once_with()

    get_answer(
        message,
    ).assert_awaited_once()


# =========================================================
# EMPTY URL
# =========================================================


@pytest.mark.asyncio
async def test_empty_proxy_url_is_rejected() -> None:
    settings = AppSettingsSchema()

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    setattr(
        message,
        "text",
        "   ",
    )

    state = build_state()

    await proxy_url_handler(
        message,
        state,
        double.context,
    )

    double.settings.set_proxy_url.assert_not_called()

    get_state_clear(
        state,
    ).assert_not_awaited()

    get_answer(
        message,
    ).assert_awaited_once()


# =========================================================
# TEST CONNECTION
# =========================================================


@pytest.mark.asyncio
async def test_proxy_connection_can_be_tested() -> None:
    settings = AppSettingsSchema(
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    connection_result = ProxyConnectionTestResult(
        status=(ProxyConnectionStatus.SUCCESS),
        duration_ms=120,
        telegram_username="test_bot",
    )

    with patch(
        ("django_assistant_bot.bot.handlers." "proxy.check_configured_proxy"),
        new=AsyncMock(
            return_value=connection_result,
        ),
    ) as connection_check:
        await proxy_test_callback(
            callback,
            double.context,
        )

    connection_check.assert_awaited_once_with(
        double.context,
    )

    get_callback_answer(
        callback,
    ).assert_awaited_once_with("در حال تست اتصال پروکسی...")

    edit_text = get_edit_text(
        message,
    )

    edit_text.assert_awaited_once()

    text = get_awaited_first_argument(
        edit_text,
    )

    assert "اتصال پروکسی موفق بود" in text


# =========================================================
# ENABLE - SUCCESS
# =========================================================


@pytest.mark.asyncio
async def test_proxy_can_be_enabled() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    connection_result = ProxyConnectionTestResult(
        status=(ProxyConnectionStatus.SUCCESS),
        duration_ms=120,
        telegram_username="test_bot",
    )

    with patch(
        ("django_assistant_bot.bot.handlers." "proxy.check_configured_proxy"),
        new=AsyncMock(
            return_value=connection_result,
        ),
    ) as connection_check:
        await proxy_enable_callback(
            callback,
            double.context,
        )

    connection_check.assert_awaited_once_with(
        double.context,
    )

    double.settings.enable_proxy.assert_called_once_with()

    get_callback_answer(
        callback,
    ).assert_awaited_once_with("در حال بررسی پروکسی...")

    edit_text = get_edit_text(
        message,
    )

    edit_text.assert_awaited_once()

    text = get_awaited_first_argument(
        edit_text,
    )

    assert "پروکسی با موفقیت" in text

    assert "فعال شد" in text


# =========================================================
# ENABLE - CONNECTION FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_failed_proxy_check_does_not_enable_proxy() -> None:
    """
    A proxy that cannot reach Telegram must never be marked
    as enabled.

    This protects the application from being locked out on
    the next restart.
    """

    settings = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    connection_result = ProxyConnectionTestResult(
        status=(ProxyConnectionStatus.NETWORK_ERROR),
        duration_ms=250,
    )

    with patch(
        ("django_assistant_bot.bot.handlers." "proxy.check_configured_proxy"),
        new=AsyncMock(
            return_value=connection_result,
        ),
    ) as connection_check:
        await proxy_enable_callback(
            callback,
            double.context,
        )

    connection_check.assert_awaited_once_with(
        double.context,
    )

    # Most important invariant:
    #
    # Failed connectivity must never persist
    # proxy_enabled=True.
    double.settings.enable_proxy.assert_not_called()

    get_callback_answer(
        callback,
    ).assert_awaited_once_with("در حال بررسی پروکسی...")

    edit_text = get_edit_text(
        message,
    )

    edit_text.assert_awaited_once()

    text = get_awaited_first_argument(
        edit_text,
    )

    assert "پروکسی فعال نشد" in text


# =========================================================
# DISABLE
# =========================================================


@pytest.mark.asyncio
async def test_proxy_can_be_disabled() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    await proxy_disable_callback(
        callback,
        double.context,
    )

    double.settings.disable_proxy.assert_called_once_with()

    get_callback_answer(
        callback,
    ).assert_awaited_once_with("پروکسی غیرفعال شد.")

    get_edit_text(
        message,
    ).assert_awaited_once()


# =========================================================
# CLEAR
# =========================================================


@pytest.mark.asyncio
async def test_proxy_can_be_cleared() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    await proxy_clear_callback(
        callback,
        double.context,
    )

    double.settings.clear_proxy.assert_called_once_with()

    get_callback_answer(
        callback,
    ).assert_awaited_once_with("پروکسی حذف شد.")

    get_edit_text(
        message,
    ).assert_awaited_once()


# =========================================================
# CANCEL
# =========================================================


@pytest.mark.asyncio
async def test_proxy_url_change_can_be_cancelled() -> None:
    settings = AppSettingsSchema(
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    callback = build_callback(
        message,
    )

    state = build_state()

    await proxy_cancel_callback(
        callback,
        state,
        double.context,
    )

    get_state_clear(
        state,
    ).assert_awaited_once_with()

    double.settings.get_settings.assert_called_once_with()

    get_callback_answer(
        callback,
    ).assert_awaited_once_with("تغییر پروکسی لغو شد.")

    get_edit_text(
        message,
    ).assert_awaited_once()


@pytest.mark.asyncio
async def test_changing_proxy_url_returns_disabled_state() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    double = ProxyContextDouble(
        settings,
    )

    message = build_message()

    setattr(
        message,
        "text",
        "socks5://127.0.0.1:1081",
    )

    state = build_state()

    await proxy_url_handler(
        message,
        state,
        double.context,
    )

    double.settings.set_proxy_url.assert_called_once_with(
        "socks5://127.0.0.1:1081",
    )

    get_state_clear(
        state,
    ).assert_awaited_once_with()

    answer = get_answer(
        message,
    )

    answer.assert_awaited_once()

    await_args = answer.await_args

    assert await_args is not None

    reply_markup = await_args.kwargs["reply_markup"]

    callbacks = [
        button.callback_data for row in reply_markup.inline_keyboard for button in row
    ]

    assert "proxy:enable" in callbacks

    assert "proxy:disable" not in callbacks
