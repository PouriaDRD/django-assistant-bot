from __future__ import annotations

from unittest.mock import patch

from django_assistant_bot.services.runtime import (
    ApplicationRuntimeService,
)


def test_get_uptime_seconds_returns_elapsed_time() -> None:
    with patch(
        ("django_assistant_bot.services." "runtime.service.time.monotonic"),
        side_effect=[
            100.0,
            125.5,
        ],
    ):
        service = ApplicationRuntimeService()

        result = service.get_uptime_seconds()

    assert result == 25.5


def test_get_uptime_seconds_never_returns_negative() -> None:
    with patch(
        ("django_assistant_bot.services." "runtime.service.time.monotonic"),
        side_effect=[
            100.0,
            90.0,
        ],
    ):
        service = ApplicationRuntimeService()

        result = service.get_uptime_seconds()

    assert result == 0.0
