from __future__ import annotations

from aiogram.fsm.state import (
    State,
    StatesGroup,
)


class ProxyState(
    StatesGroup,
):
    """
    FSM states used by proxy management flows.
    """

    waiting_for_proxy_url = State()


__all__ = [
    "ProxyState",
]
