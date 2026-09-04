from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)

from aiogram.types import (
    InlineKeyboardMarkup,
)

from django_assistant_bot.bot.keyboards.admins import (
    ADMIN_ADD_CALLBACK,
    ADMIN_DELETE_PREFIX,
    ADMINS_CALLBACK,
    admin_creation_keyboard,
    admin_delete_keyboard,
    admins_menu_keyboard,
)
from django_assistant_bot.schemas.admin import (
    AdminSchema,
)


def build_admin(
    telegram_user_id: int,
) -> AdminSchema:
    return AdminSchema(
        telegram_user_id=telegram_user_id,
        created_at=datetime.now(
            UTC,
        ),
    )


def callback_data(
    keyboard: InlineKeyboardMarkup,
) -> list[str]:
    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


def test_admins_menu_with_single_admin() -> None:
    keyboard = admins_menu_keyboard(
        [
            build_admin(
                111,
            ),
        ]
    )

    callbacks = callback_data(
        keyboard,
    )

    assert ADMIN_ADD_CALLBACK in callbacks

    assert "admin:delete:list" not in callbacks

    assert "main:menu" in callbacks


def test_admins_menu_with_multiple_admins() -> None:
    keyboard = admins_menu_keyboard(
        [
            build_admin(
                111,
            ),
            build_admin(
                222,
            ),
        ]
    )

    callbacks = callback_data(
        keyboard,
    )

    assert "admin:delete:list" in callbacks


def test_admin_delete_keyboard() -> None:
    keyboard = admin_delete_keyboard(
        [
            build_admin(
                111,
            ),
            build_admin(
                222,
            ),
        ]
    )

    callbacks = callback_data(
        keyboard,
    )

    assert f"{ADMIN_DELETE_PREFIX}111" in callbacks

    assert f"{ADMIN_DELETE_PREFIX}222" in callbacks

    assert ADMINS_CALLBACK in callbacks


def test_admin_creation_keyboard() -> None:
    keyboard = admin_creation_keyboard()

    callbacks = callback_data(
        keyboard,
    )

    assert callbacks == [
        "admin:cancel",
    ]


def test_admin_callbacks_fit_telegram_limit() -> None:
    keyboards = [
        admins_menu_keyboard(
            [
                build_admin(
                    111,
                ),
                build_admin(
                    222,
                ),
            ]
        ),
        admin_delete_keyboard(
            [
                build_admin(
                    111,
                ),
                build_admin(
                    222,
                ),
            ]
        ),
        admin_creation_keyboard(),
    ]

    for keyboard in keyboards:
        for callback in callback_data(
            keyboard,
        ):
            assert len(callback.encode("utf-8")) <= 64
