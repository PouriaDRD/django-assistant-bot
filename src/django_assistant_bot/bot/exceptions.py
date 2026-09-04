from __future__ import annotations

# =========================================================
# BASE ERROR
# =========================================================


class TelegramBotError(Exception):
    """
    Base exception for Telegram bot infrastructure errors.
    """


# =========================================================
# STARTUP ERROR
# =========================================================


class TelegramStartupError(
    TelegramBotError,
):
    """
    Raised when Telegram transport cannot start safely.

    The exception message must never contain raw proxy URLs,
    credentials, tokens, or low-level networking details.
    """


__all__ = [
    "TelegramBotError",
    "TelegramStartupError",
]
