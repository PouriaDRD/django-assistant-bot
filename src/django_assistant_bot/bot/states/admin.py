from __future__ import annotations

from aiogram.fsm.state import (
    State,
    StatesGroup,
)


class AdminManagementState(StatesGroup):
    """
    States used during Telegram administrator management.
    """

    waiting_for_user_id = State()


__all__ = [
    "AdminManagementState",
]
