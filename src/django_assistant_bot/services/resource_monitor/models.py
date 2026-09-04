from __future__ import annotations

from dataclasses import (
    dataclass,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProcessResourceSnapshot:
    """
    Point-in-time resource usage for the current process.
    """

    rss_bytes: int

    vms_bytes: int

    cpu_percent: float

    thread_count: int

    open_file_count: int

    read_bytes: int

    write_bytes: int


@dataclass(
    frozen=True,
    slots=True,
)
class ProcessResourceDelta:
    """
    Resource difference between two process snapshots.
    """

    rss_bytes: int

    vms_bytes: int

    thread_count: int

    open_file_count: int

    read_bytes: int

    write_bytes: int


__all__ = [
    "ProcessResourceDelta",
    "ProcessResourceSnapshot",
]
