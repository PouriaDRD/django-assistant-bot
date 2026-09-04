from __future__ import annotations

import time
from collections.abc import (
    Callable,
)
from dataclasses import (
    dataclass,
)

from django_assistant_bot.services.backup.models import (
    BackupResult,
)
from django_assistant_bot.services.resource_monitor.service import (
    ProcessResourceMonitor,
)


@dataclass(
    frozen=True,
    slots=True,
)
class BackupBenchmarkResult:
    """
    Measured resource usage for one backup execution.
    """

    duration_seconds: float

    rss_before_bytes: int

    rss_after_bytes: int

    rss_delta_bytes: int

    thread_delta: int

    read_bytes: int

    write_bytes: int

    database_size_bytes: int

    media_size_bytes: int

    archive_size_bytes: int

    media_file_count: int

    compression_ratio: float


def benchmark_backup(
    *,
    run_backup: Callable[
        [],
        BackupResult,
    ],
    monitor: ProcessResourceMonitor | None = None,
) -> tuple[
    BackupResult,
    BackupBenchmarkResult,
]:
    """
    Execute one backup and measure current-process
    resource usage around it.
    """

    resource_monitor = monitor if monitor is not None else ProcessResourceMonitor()

    before = resource_monitor.snapshot()

    started_at = time.perf_counter()

    result = run_backup()

    duration = time.perf_counter() - started_at

    after = resource_monitor.snapshot()

    delta = resource_monitor.delta(
        before=before,
        after=after,
    )

    source_size = result.database_size_bytes + result.media_size_bytes

    compression_ratio = (
        (result.archive_size_bytes / source_size) if source_size > 0 else 0.0
    )

    benchmark = BackupBenchmarkResult(
        duration_seconds=duration,
        rss_before_bytes=(before.rss_bytes),
        rss_after_bytes=(after.rss_bytes),
        rss_delta_bytes=(delta.rss_bytes),
        thread_delta=(delta.thread_count),
        read_bytes=(delta.read_bytes),
        write_bytes=(delta.write_bytes),
        database_size_bytes=(result.database_size_bytes),
        media_size_bytes=(result.media_size_bytes),
        archive_size_bytes=(result.archive_size_bytes),
        media_file_count=(result.media_file_count),
        compression_ratio=(compression_ratio),
    )

    return (
        result,
        benchmark,
    )


__all__ = [
    "BackupBenchmarkResult",
    "benchmark_backup",
]
