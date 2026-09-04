from __future__ import annotations

import os

import psutil

from django_assistant_bot.services.resource_monitor.models import (
    ProcessResourceDelta,
    ProcessResourceSnapshot,
)


class ProcessResourceMonitor:
    """
    Measure resource usage of the current application process.

    This service is intentionally read-only and does not
    modify process or operating-system state.
    """

    def __init__(
        self,
        process: psutil.Process | None = None,
    ) -> None:
        self._process = (
            process
            if process is not None
            else psutil.Process(
                os.getpid(),
            )
        )

    def snapshot(
        self,
    ) -> ProcessResourceSnapshot:
        """
        Capture one process resource snapshot.
        """

        memory = self._process.memory_info()

        io = self._get_io_counters()

        return ProcessResourceSnapshot(
            rss_bytes=memory.rss,
            vms_bytes=memory.vms,
            cpu_percent=(
                self._process.cpu_percent(
                    interval=None,
                )
            ),
            thread_count=(self._process.num_threads()),
            open_file_count=(self._get_open_file_count()),
            read_bytes=io[0],
            write_bytes=io[1],
        )

    @staticmethod
    def delta(
        *,
        before: ProcessResourceSnapshot,
        after: ProcessResourceSnapshot,
    ) -> ProcessResourceDelta:
        """
        Calculate resource changes between two snapshots.
        """

        return ProcessResourceDelta(
            rss_bytes=(after.rss_bytes - before.rss_bytes),
            vms_bytes=(after.vms_bytes - before.vms_bytes),
            thread_count=(after.thread_count - before.thread_count),
            open_file_count=(after.open_file_count - before.open_file_count),
            read_bytes=max(
                0,
                after.read_bytes - before.read_bytes,
            ),
            write_bytes=max(
                0,
                after.write_bytes - before.write_bytes,
            ),
        )

    def _get_open_file_count(
        self,
    ) -> int:
        """
        Return current process open-file count.

        Some platforms may deny access to this information;
        resource monitoring must not break the application.
        """

        try:
            return len(self._process.open_files())

        except (
            psutil.AccessDenied,
            psutil.NoSuchProcess,
        ):
            return 0

    def _get_io_counters(
        self,
    ) -> tuple[int, int]:
        """
        Return process read/write byte counters.

        Unsupported or inaccessible platforms return zeroes.
        """

        try:
            counters = self._process.io_counters()

        except (
            AttributeError,
            psutil.AccessDenied,
            psutil.NoSuchProcess,
        ):
            return (
                0,
                0,
            )

        return (
            counters.read_bytes,
            counters.write_bytes,
        )


__all__ = [
    "ProcessResourceMonitor",
]
