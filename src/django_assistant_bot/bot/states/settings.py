from __future__ import annotations

from aiogram.fsm.state import (
    State,
    StatesGroup,
)


class SettingsState(
    StatesGroup,
):
    """
    FSM states used by runtime settings flows.
    """

    waiting_for_retention_keep_last = State()


__all__ = [
    "SettingsState",
]
