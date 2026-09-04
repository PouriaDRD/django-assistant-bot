from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class DeliveryResult:
    """
    Result of delivering one backup to recipients.
    """

    attempted: int

    succeeded: int

    failed: int

    skipped: int = 0

    @property
    def is_successful(self) -> bool:
        return self.attempted > 0 and self.failed == 0

    @property
    def is_partial(self) -> bool:
        return self.succeeded > 0 and self.failed > 0
