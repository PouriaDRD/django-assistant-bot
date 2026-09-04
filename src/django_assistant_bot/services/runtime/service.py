from __future__ import annotations

import time


class ApplicationRuntimeService:
    """
    Track application runtime duration.

    A monotonic clock is used so uptime is not affected by
    operating-system clock adjustments.
    """

    def __init__(
        self,
    ) -> None:
        self._started_at = time.monotonic()

    def get_uptime_seconds(
        self,
    ) -> float:
        """
        Return application uptime in seconds.
        """

        uptime = time.monotonic() - self._started_at

        return max(
            0.0,
            uptime,
        )


__all__ = [
    "ApplicationRuntimeService",
]
